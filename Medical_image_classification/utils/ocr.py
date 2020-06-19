"""
 -- author : Anish Basnet
 -- email : anishbasnetworld@gmail.com
 -- date : 11/1/2019
"""

import pytesseract


def image2text(filename):
    return pytesseract.image_to_string(filename)


def image2data(filename):
    return pytesseract.image_to_data(filename)
