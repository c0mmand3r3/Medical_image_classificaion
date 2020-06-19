"""
-- author: Anish Basnet
-- email: anishbasnetworld@gmail.com
-- Date: 5/9/19
"""
import logging
from string import punctuation, whitespace

import PyPDF2

from Medical_image_classification.utils.ocr import image2text
from Medical_image_classification.utils.utils import format_layout

logger = logging.getLogger(__name__)


def read_document(filename):
    """
    :param filename: pdf or image
    :return:
    """
    pages = []
    try:
        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfFileReader(open(filename, mode='rb'))
            for i in range(pdf_reader.getNumPages()):
                doc = pdf_reader.getPage(i).extractText()
                if len(str(doc).strip()) > 0:
                    pages.append(doc)

            if len(pages) == 0:  # pdf contain images TODO optimize for image containing condition
                images = extract_images_from_pdf_fitz(filename)
                for image in images:
                    if image is not None:
                        pages.append(image2text(image))

        elif filename.endswith(tuple(['.jpg', '.jpeg', '.png', '.JPG', '.JPEG'])):
            data = image2text(filename)
            pages.append(data)
        else:
            logger.error("Unknown document format. File: {}", filename)
    except Exception as e:
        logger.exception(e)
    return pages


def extract_images_from_pdf_pypdf2(filename):
    images = []
    pdfReader = PyPDF2.PdfFileReader(open(filename, mode='rb'))
    for i in range(pdfReader.getNumPages()):
        page = pdfReader.getPage(i)
        if '/XObject' in page['/Resources']:
            xObject = page['/Resources']['/XObject'].getObject()
            for obj in xObject:
                from PIL import Image
                if xObject[obj]['/Subtype'] == '/Image':
                    size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                    data = xObject[obj].getData()

                    if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                        mode = "RGB"
                    else:
                        mode = "P"

                    if '/Filter' in xObject[obj]:
                        if xObject[obj]['/Filter'] == '/FlateDecode':
                            img = Image.frombytes(mode, size, data)
                            img.save(obj[1:] + ".png")
                            images.append(obj[1:] + ".png")
                        elif xObject[obj]['/Filter'] == '/DCTDecode':
                            img = open(obj[1:] + ".jpg", "wb")
                            img.write(data)
                            img.close()
                            images.append(obj[1:] + ".jpg")
                        elif xObject[obj]['/Filter'] == '/JPXDecode':
                            img = open(obj[1:] + ".jp2", "wb")
                            img.write(data)
                            img.close()
                            images.append(obj[1:] + ".jp2")
                        elif xObject[obj]['/Filter'] == '/CCITTFaxDecode':
                            img = open(obj[1:] + ".tiff", "wb")
                            img.write(data)
                            img.close()
                            images.append(obj[1:] + ".tiff")
                    else:
                        img = Image.frombytes(mode, size, data)
                        img.save(obj[1:] + ".png")
                        images.append(obj[1:] + ".png")
    return images


def extract_images_from_pdf_fitz(filename, output_dir=None):
    import fitz
    doc = fitz.open(filename)
    images = []
    if output_dir is None:
        output_dir = "/tmp"
    for i in range(len(doc)):
        for j, img in enumerate(doc.getPageImageList(i)):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            name = "{}/p{}_{}.png".format(output_dir, i, j)
            if pix.n < 5:  # this is GRAY or RGB
                pix.writePNG(name)
            else:  # CMYK: convert to RGB first
                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                pix1.writePNG(name)
            images.append(name)
    return images


def find_text(text, prefix_suffix):
    """
    :param text:
    :param prefix_suffix: (prefix, suffix)
    :return:
    """
    if prefix_suffix[0] is None and prefix_suffix[1] is None:
        return ""
    import re
    if prefix_suffix[0] is None:
        regex = "\n" + '(.+?)' + prefix_suffix[1]
    elif prefix_suffix[1] is None:
        regex = prefix_suffix[0] + '(.+?)' + "\n"
    else:
        regex = prefix_suffix[0] + '((.|\n)*)' + prefix_suffix[1]
    try:
        found = re.search(regex, text, re.IGNORECASE and re.MULTILINE).group(1)
    except AttributeError:
        found = ''

    found = found.replace("\n", "").strip()
    return found


def convert_pdf_to_images(filename, output_dir):
    from pdf2image import convert_from_path
    pages = convert_from_path(filename)

    for i, page in enumerate(pages):
        name = "{}/page_{}.jpg".format(output_dir, i)
        page.save(name, 'JPEG')


def read_pdf_with_pypdf2(filename, page_numbers=None, page_portion=1,
                         first_page_only=False, last_page_only=False):
    text = ""
    try:
        pdf_reader = PyPDF2.PdfFileReader(open(filename, mode='rb'))

        if first_page_only:
            page_numbers = [1]
        elif last_page_only:  # TODO
            raise KeyError
        if 1 > page_portion > 0:  # TODO
            pass

        for page_number in page_numbers:
            page = pdf_reader.getPage(page_number - 1).extractText()
            text += page
            text += "\n"
    except Exception as e:
        logger.error("Error while reading the pdf file {}".format(filename), e)
    return text


def read_pdf_with_pdfbox(filename, page_numbers=None, page_portion=1,
                         first_page_only=False, last_page_only=False):
    import pdfbox
    p = pdfbox.PDFBox()
    text = ""
    try:
        text = p.extract_text(filename, start_page=1, end_page=1)
        if text is None:
            with open(str(filename[:-3] + "txt")) as fp:
                text = fp.read()
    except Exception as e:
        logger.error("Error while reading the pdf file {}".format(filename), e)
    return text


def read_pdf_with_pdfminer_v0(filename, page_numbers=None, page_portion=1,
                              first_page_only=False, last_page_only=False):
    """
    This methods convert the pdf to text using pdfminer module.
    :param last_page_only:
    :param first_page_only:
    :param page_portion:
    :param page_numbers:
    :param filename:
    :param page_numbers:
    :return:
    """
    text = ""
    try:
        from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
        from pdfminer.pdfpage import PDFPage
        from pdfminer.converter import TextConverter
        from pdfminer.layout import LAParams
        from pdfminer.converter import PDFPageAggregator
        from pdfminer.layout import LTTextBoxHorizontal
        import io
        fp = open(filename, 'rb')
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        # Create a PDF interpreter object.
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        if first_page_only:
            page_numbers = [1]
        elif last_page_only:  # TODO
            raise KeyError
        if page_portion > 1 or page_portion < 0:  # TODO
            logger.error("Page portion should be between 0 to 1")
            return ""

        if page_numbers is None:
            for page_number, page in enumerate(PDFPage.get_pages(fp)):
                page_height = page.mediabox[3]
                page_portion_height = int(page_height * page_portion)
                interpreter.process_page(page)
                layout = device.get_result()
                for lobj in layout:
                    if isinstance(lobj, LTTextBoxHorizontal):
                        # left, bottom, right, top = lobj.bbox
                        # The y-coordinates are given as the distance from the bottom of the page
                        x, y = lobj.bbox[0], lobj.bbox[3]
                        # Get height from top
                        y = page.mediabox[3] - y
                        if y <= page_portion_height:
                            text += lobj.get_text()
                            text += "\n"
        else:
            page_numbers = list(map(lambda x: x - 1, page_numbers))
            for page_number, page in enumerate(PDFPage.get_pages(fp)):
                page_height = page.mediabox[3]
                print("PAge height", page_height)
                page_portion_height = int(page_height * page_portion)
                if page_number in page_numbers:
                    interpreter.process_page(page)
                    layout = device.get_result()
                    for lobj in layout:
                        print(lobj)

                        if isinstance(lobj, LTTextBoxHorizontal):
                            print("HI", lobj._objs)
                            # left, bottom, right, top = lobj.bbox
                            # The y-coordinates are given as the distance from the bottom of the page
                            x, y = lobj.bbox[0], lobj.bbox[3]
                            # Get height from top
                            y = page.mediabox[3] - y
                            print("Height compare", y, page_portion_height)
                            if y <= page_portion_height:
                                text += lobj.get_text()
                                text += "\n"
        # # page portion based on length of document
        # len_text =len(text)
        # text_portion = int(len_text * page_portion)
        # text = text[:text_portion]
    except Exception as e:
        logger.error("Error while reading the pdf file {}".format(filename), e)
    return text


def read_pdf_with_pdfminer(filename, page_numbers=None, page_portion=1.0):
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfinterp import PDFPageInterpreter
    from pdfminer.pdfinterp import PDFResourceManager
    from pdfminer.layout import LAParams
    from pdfminer.converter import PDFPageAggregator
    from pdfminer.layout import LTTextBoxHorizontal
    from news_classification.entities.page_layout import TextBlock
    from news_classification.entities.page_layout import Word
    from pdfminer.layout import LTTextLineHorizontal
    from pdfminer.layout import LTChar
    from news_classification.entities.page_layout import PageLayout

    fp = open(filename, 'rb')
    # Create resource manager
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.
    laparams = LAParams()
    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    page_layout = PageLayout()
    page_layout.text = ""
    if page_numbers is not None:
        page_numbers = list(map(lambda x: x - 1, page_numbers))
    for page_number, page in enumerate(PDFPage.get_pages(fp)):
        if page_numbers is None or page_number in page_numbers:
            block_id = 0
            page_height = page.mediabox[3]
            page_portion_height = int(page_height * page_portion)
            interpreter.process_page(page)
            # receive the LTPage object for the page.
            layout = device.get_result()
            blocks = []
            for element in layout:
                if isinstance(element, LTTextBoxHorizontal):
                    block = TextBlock(id=block_id)
                    block.text = ""
                    l, b, r, t = element.bbox
                    # Get height from the top
                    b = page_height - b
                    t = page_height - t
                    # Saving in left top right bottom format
                    block_id += 1
                    words = []
                    for obj in element:
                        if isinstance(obj, LTTextLineHorizontal):

                            word = Word()
                            l, b, r, t = obj.bbox
                            # Get height from the top
                            b = page_height - b
                            t = page_height - t
                            # print("text", obj.get_text())
                            # Saving in left top right bottom format
                            if b > page_portion_height:
                                # print("Yes")
                                continue
                            word.bbox = [l, t, r, b]
                            word.text = obj.get_text()
                            block.text += word.text
                            char_length = 0
                            word_height = 0
                            font = None
                            for c in obj:
                                if isinstance(c, LTChar):
                                    if c.get_text() in punctuation or c.get_text() in whitespace:
                                        continue
                                    word_height += c.adv
                                    char_length += 1
                                    font = c.fontname
                            word.text_size = word_height / char_length if char_length != 0 else 0
                            word.font_type = font
                            words.append(word)
                    # print("words", words)
                    if len(words) > 0:
                        block.bbox = [l, t, r, b]
                        block.words = words
                        blocks.append(block)
                        page_layout.text += block.text
            page_layout.blocks = blocks
            page_layout.text = format_layout(page_layout)
            return page_layout


def read_pdf(filenames=None, page_numbers=None, page_portion=1.0, first_page_only=False, last_page_only=False):
    """
    This method takes the pdf file list with their certain page number and provides extract text from it.
    :param last_page_only:
    :param first_page_only:
    :param page_portion: (0,1] page portion (%) to consider. Default 1 = 100% TODO
    :param filenames: List -> ['path',....,'path']
    :param page_numbers: List of page numbers to extract.
    :return:
    """

    if first_page_only:
        page_numbers = [1]
    elif last_page_only:  # TODO
        raise KeyError
    if page_portion > 1 or page_portion < 0:  # TODO
        logger.error("Page portion should be between 0 to 1")
        return ""
    documents = []
    if filenames is not None:
        for filename in filenames:
            result = read_pdf_with_pdfminer(filename, page_numbers=page_numbers, page_portion=page_portion)
            documents.append(result)
        return documents
    else:
        return documents
