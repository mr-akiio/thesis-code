from sec_certs.dataset.cc import CCDataset
import pandas as pd
from .manufacturer_cleanup import unify_manufacturer

def get_library_mentions(dataset: CCDataset, name: str) -> pd.DataFrame:
    columns = ['Library', 'Manufacturer', 'IssueDate', 'SunsetDate', f"{name}Mentioned", f"{name}MentionedReport", f"{name}MentionedTarget", 'Country', 'Category']


    result = pd.DataFrame(columns=columns)

    for cert in dataset:
        list_of_libs, list_of_libs_2 = 0,0

        if cert.pdf_data.report_keywords not in [None, []]:
            if name in cert.pdf_data.report_keywords["crypto_library"]:
                list_of_libs = cert.pdf_data.report_keywords["crypto_library"][name][name]
        
        if cert.pdf_data.st_keywords not in [None, []]:
            if name in cert.pdf_data.st_keywords["crypto_library"]:
                list_of_libs_2 = cert.pdf_data.st_keywords["crypto_library"][name][name]

        if list_of_libs > 0 or list_of_libs_2 > 0:
            result.loc[len(result)] = [name, 
                                       unify_manufacturer(cert.manufacturer),
                                       cert.not_valid_before,
                                       cert.not_valid_after,
                                       1,
                                       list_of_libs,
                                       list_of_libs_2,
                                       cert.scheme,
                                       cert.category
                                       ]

    return result