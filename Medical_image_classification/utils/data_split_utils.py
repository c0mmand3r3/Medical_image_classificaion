"""
 -- author : Anish Basnet
 -- email : anishbasnetworld@gmail.com
 -- date : March 15, 2020
"""
import os

import numpy as np

from Medical_image_classification.utils import get_all_files


def split_document_based_data_set(split_documents=None, ratio=None, verbose=False):
    """
    This function split the documents based on the split ratio.
    :param split_documents: list -> [doc1, doc2, doc3 .. ] : List of the documents.
    :param ratio: float -> 0.9 : It means, 90% training and 10% testing.
    :param verbose: boolean -> True or False : It helps to keep the track of the split documents.
    :return: list, list -> train, test : first list is for training documents and second list is for testing documents.
    """
    total_document = len(split_documents)
    total_train_document = int(ratio * total_document)
    split_train = np.random.choice(split_documents, total_train_document, replace=False)
    split_test = np.array(list(set(split_documents).difference(set(split_train))))
    if verbose:
        print("{} - {} -> Total : {}\nTrain Files - {}\n Test Files -{}"
              .format(len(split_train), len(split_test), total_document, split_train, split_test))
    return split_train, split_test


def get_lowest_document_information(root_path=None, targets=None, verbose=True):
    documents_count = []
    for target in targets:
        files = get_all_files(os.path.join(root_path, target))
        if verbose:
            print("Target Directory : {} - Documents : {}".format(target, len(files)))
        documents_count.append(len(files))
    return min(documents_count)
