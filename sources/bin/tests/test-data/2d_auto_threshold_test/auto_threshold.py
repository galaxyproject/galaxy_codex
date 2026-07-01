"""
Copyright 2017-2022 Biomedical Computer Vision Group, Heidelberg University.

Distributed under the MIT license.
See file LICENSE for detail or copy at https://opensource.org/licenses/MIT

"""

import argparse

import skimage.filters
import skimage.io
import skimage.util
import tifffile

thOptions = {
    "otsu": lambda img_raw, bz: skimage.filters.threshold_otsu(img_raw),
    "li": lambda img_raw, bz: skimage.filters.threshold_li(img_raw),
    "yen": lambda img_raw, bz: skimage.filters.threshold_yen(img_raw),
    "isodata": lambda img_raw, bz: skimage.filters.threshold_isodata(img_raw),
    "loc_gaussian": lambda img_raw, bz: skimage.filters.threshold_local(img_raw, bz, method="gaussian"),
    "loc_median": lambda img_raw, bz: skimage.filters.threshold_local(img_raw, bz, method="median"),
    "loc_mean": lambda img_raw, bz: skimage.filters.threshold_local(img_raw, bz, method="mean"),
}


def auto_thresholding(in_fn, out_fn, th_method, block_size=5, dark_bg=True):  # type: ignore[no-untyped-def]
    img = skimage.io.imread(in_fn)
    th = thOptions[th_method](img, block_size)
    if dark_bg:
        res = img > th
    else:
        res = img <= th
    tifffile.imwrite(out_fn, skimage.util.img_as_ubyte(res))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automatic Image Thresholding")
    parser.add_argument("im_in", help="Path to the input image")
    parser.add_argument("im_out", help="Path to the output image (TIFF)")
    parser.add_argument("th_method", choices=thOptions.keys(), help="Thresholding method")
    parser.add_argument(
        "block_size", type=int, default=5, help="Odd size of pixel neighborhood for calculating the threshold"
    )
    parser.add_argument("dark_bg", default=True, type=bool, help="True if background is dark")
    args = parser.parse_args()

    auto_thresholding(args.im_in, args.im_out, args.th_method, args.block_size, args.dark_bg)
