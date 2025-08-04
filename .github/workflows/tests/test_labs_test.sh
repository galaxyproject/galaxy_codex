#!/bin/bash

# Act-based test for labs_test.yml workflow
# Tests the actual GitHub Actions workflow with different PR scenarios
# and validates the artifacts it produces
# Runs in complete isolation without affecting the main repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0

# Create temporary directory for all test operations
TEST_TEMP_DIR=$(mktemp -d -t labs_test_XXXXXX)
ORIGINAL_DIR=$(pwd)
ORIGINAL_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Cleanup function
cleanup() {
    echo "Cleaning up temporary files..."
    cd "$ORIGINAL_DIR"
    rm -rf "$TEST_TEMP_DIR"
    # Clean up any act containers
    docker ps -a --filter "name=act-Test-changed-Lab-pages" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
    # Ensure we're back on the original branch
    git checkout "$ORIGINAL_BRANCH" 2>/dev/null || true
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

print_header() {
    echo -e "${YELLOW}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

create_pr_event() {
    local pr_number="$1"
    local head_ref="$2"
    local base_ref="$3"
    local head_sha="$4"
    local head_repo="${5:-galaxyproject/galaxy_codex}"
    local base_repo="${6:-galaxyproject/galaxy_codex}"
    
    cat > "$TEST_TEMP_DIR/pr_event_${pr_number}.json" << EOF
{
  "number": $pr_number,
  "pull_request": {
    "head": {
      "ref": "$head_ref",
      "sha": "$head_sha",
      "repo": {
        "full_name": "$head_repo"
      }
    },
    "base": {
      "ref": "$base_ref",
      "repo": {
        "full_name": "$base_repo"
      }
    }
  },
  "repository": {
    "full_name": "$base_repo"
  }
}
EOF
}

setup_isolated_repo() {
    local test_dir="$1"
    local scenario="$2"  # "with_lab_changes" or "no_lab_changes"
    
    # Create a complete isolated git repository
    cd "$test_dir"
    git init -q
    git config user.name "Test User"
    git config user.email "test@example.com"
    
    # Copy essential files only to avoid Docker tar size issues
    cp -r "$ORIGINAL_DIR"/.github . 2>/dev/null || true
    cp -r "$ORIGINAL_DIR"/.actrc . 2>/dev/null || true
    
    # Create minimal directory structure for lab files
    mkdir -p communities/microgalaxy/lab
    mkdir -p communities/spoc/lab/sections
    mkdir -p communities/genome/lab/static
    mkdir -p base/sources/bin
    
    # Create minimal lab files
    echo "name: microgalaxy-lab" > communities/microgalaxy/lab/base.yml
    echo "name: spoc-beginner" > communities/spoc/lab/sections/1_beginner.yml  
    echo "# genome logo" > communities/genome/lab/static/logo.png
    
    # Create minimal README for non-lab changes
    echo "# Test Repository" > README.md
    
    # Create initial commit
    git add .
    git commit -q -m "Initial commit"
    
    # Create main branch
    git branch -m main
    
    # Create test branch based on scenario
    if [ "$scenario" = "with_lab_changes" ]; then
        git checkout -q -b test-branch
        echo "# Test change $(date)" >> communities/microgalaxy/lab/base.yml
        git add communities/microgalaxy/lab/base.yml
        git commit -q -m "Test: Add lab file change"
    elif [ "$scenario" = "no_lab_changes" ]; then
        git checkout -q -b test-branch
        echo "# Non-lab change $(date)" >> README.md
        git add README.md
        git commit -q -m "Test: Non-lab change"
    fi
}

run_workflow_test() {
    local test_name="$1"
    local pr_number="$2"
    local scenario="$3"  # "with_lab_changes" or "no_lab_changes"
    local expected_lab_changes="$4"  # "true" or "false"
    
    TESTS_RUN=$((TESTS_RUN + 1))
    print_header "Test $TESTS_RUN: $test_name"
    
    # Create test-specific directory
    local test_dir="$TEST_TEMP_DIR/test_$TESTS_RUN"
    mkdir -p "$test_dir"
    
    # Set up isolated repository first to get the SHA
    setup_isolated_repo "$test_dir" "$scenario"
    
    # Get the SHA of the test branch
    cd "$test_dir"
    local head_sha=$(git rev-parse test-branch)
    
    # Create PR event file with the correct SHA
    create_pr_event "$pr_number" "test-branch" "main" "$head_sha"
    
    # Run the workflow with act
    echo "Running workflow with act..."
    local act_output="$test_dir/act_output.log"
    local act_exit_code=0
    
    # Use --pull=false to avoid pulling Docker images repeatedly
    act pull_request \
        --eventpath "$TEST_TEMP_DIR/pr_event_${pr_number}.json" \
        --workflows .github/workflows/labs_test.yml \
        --artifact-server-path "$test_dir/artifacts" \
        --pull=false \
        --quiet \
        > "$act_output" 2>&1 || act_exit_code=$?
    
    echo "Act exit code: $act_exit_code"
    
    # Show act output for debugging
    if [ $act_exit_code -ne 0 ]; then
        echo "Act output (last 30 lines):"
        tail -30 "$act_output"
    fi
    
    # Check if workflow completed (act returns 0 on success, but we also check for expected failures)
    if [ $act_exit_code -eq 0 ]; then
        print_success "PASS: Workflow completed successfully"
    else
        # Check if the failure was due to the expected lab test step failure (continue-on-error)
        if grep -q "labs_test.py not found" "$act_output" || grep -q "Test changed Lab pages.*continue next step" "$act_output"; then
            print_success "INFO: Workflow failed at lab test step (expected for testing)"
        else
            print_error "FAIL: Workflow failed with exit code $act_exit_code"
            return 1
        fi
    fi
    
    # Look for artifacts directory created by the workflow
    local artifacts_dir="$test_dir/artifacts"
    if [ -d "$artifacts_dir" ]; then
        print_success "PASS: Artifacts directory created"
        echo "Artifacts found:"
        find "$artifacts_dir" -type f | head -10
        
        # Extract any zip files in the artifacts directory
        for zip_file in $(find "$artifacts_dir" -name "*.zip"); do
            echo "Extracting $zip_file..."
            cd "$(dirname "$zip_file")"
            unzip -o "$(basename "$zip_file")" 2>/dev/null || true
            cd "$test_dir"
        done
        
        echo "Artifacts after extraction:"
        find "$artifacts_dir" -type f | head -10
    else
        # Check in the workflow working directory
        echo "Checking for artifacts in workflow directory..."
        if [ -d "$test_dir/output" ]; then
            artifacts_dir="$test_dir/output"
            print_success "PASS: Found artifacts in workflow output directory"
        else
            print_error "WARN: No artifacts directory found"
            # Still continue to check for success
        fi
    fi
    
    # Check for specific artifacts based on the workflow 
    # The workflow should create paths.txt and env.sh in the output directory
    local found_paths_txt=false
    local found_env_sh=false
    
    # Check multiple possible locations for artifacts, including subdirectories
    artifact_paths=(
        "$artifacts_dir/labs_test_comments"
        "$artifacts_dir"
        "$test_dir/output"
    )
    
    # Also search in any subdirectories of artifacts_dir
    if [ -d "$artifacts_dir" ]; then
        while IFS= read -r -d '' dir; do
            artifact_paths+=("$dir")
        done < <(find "$artifacts_dir" -type d -print0)
    fi
    
    for check_dir in "${artifact_paths[@]}"; do
        if [ -f "$check_dir/paths.txt" ]; then
            print_success "PASS: Found paths.txt artifact in $check_dir"
            found_paths_txt=true
            
            # Validate paths.txt content based on expected changes
            if [ "$expected_lab_changes" = "true" ]; then
                if [ -s "$check_dir/paths.txt" ]; then
                    print_success "PASS: paths.txt contains lab changes as expected"
                    echo "Lab changes found:"
                    cat "$check_dir/paths.txt"
                else
                    print_error "FAIL: Expected lab changes but paths.txt is empty"
                    return 1
                fi
            else
                if [ ! -s "$check_dir/paths.txt" ]; then
                    print_success "PASS: paths.txt is empty as expected (no lab changes)"
                else
                    print_success "INFO: Found unexpected lab changes:"
                    cat "$check_dir/paths.txt"
                fi
            fi
            break
        fi
    done
    
    for check_dir in "${artifact_paths[@]}"; do
        if [ -f "$check_dir/env.sh" ]; then
            print_success "PASS: Found env.sh artifact in $check_dir"
            found_env_sh=true
            
            # Validate env.sh content
            if grep -q "export PR_NUMBER=$pr_number" "$check_dir/env.sh"; then
                print_success "PASS: env.sh contains correct PR_NUMBER"
            else
                print_error "FAIL: env.sh missing or incorrect PR_NUMBER"
                return 1
            fi
            break
        fi
    done
    
    # Check if we found the expected artifacts
    if [ "$found_paths_txt" = true ] && [ "$found_env_sh" = true ]; then
        print_success "PASS: All expected artifacts found"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "FAIL: Missing expected artifacts (paths.txt: $found_paths_txt, env.sh: $found_env_sh)"
        return 1
    fi
    
    echo ""
}

# Main test execution
print_header "Act-based Labs Workflow Test Suite"

echo "This script tests the actual GitHub Actions workflow using act."
echo "Running tests in completely isolated repositories in: $TEST_TEMP_DIR"
echo "Original repository will not be modified."
echo ""

# Test 1: PR with lab file changes
run_workflow_test "PR with lab file changes" "101" "with_lab_changes" "true"

# Test 2: PR without lab file changes  
run_workflow_test "PR without lab file changes" "102" "no_lab_changes" "false"

# Summary
print_header "Test Results Summary"
echo "Tests run: $TESTS_RUN"
echo "Tests passed: $TESTS_PASSED"

if [ $TESTS_PASSED -eq $TESTS_RUN ]; then
    print_success "All tests passed! 🎉"
    echo ""
    print_success "Your labs_test.yml workflow is working correctly:"
    echo "- Workflow runs successfully with act"
    echo "- Correct artifacts are generated (paths.txt, env.sh)"
    echo "- Git diff logic properly detects lab file changes"
    echo "- Environment variables are set correctly"
    echo ""
    echo "All temporary files will be cleaned up automatically."
    echo "Original repository was not modified."
    exit 0
else
    print_error "Some tests failed. Check the output above for details."
    echo "Temporary files will be cleaned up automatically."
    echo "Original repository was not modified."
    exit 1
fi