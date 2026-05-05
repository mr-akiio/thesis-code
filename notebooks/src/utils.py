from sec_certs.dataset.cc import CCDataset
from sec_certs.dataset.fips import FIPSDataset
import pandas as pd
from .manufacturer_cleanup import unify_manufacturer

def get_cc_library_mentions(dataset: CCDataset, name: str) -> pd.DataFrame:
    columns = ['Library', 'Manufacturer', 'IssueDate', 'SunsetDate', f"{name}MentionedReport", f"{name}MentionedTarget", 'Country', 'Category']


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
                                       list_of_libs,
                                       list_of_libs_2,
                                       cert.scheme,
                                       cert.category
                                       ]

    return result

def get_fips_library_mentions(dataset: FIPSDataset, name: str) -> pd.DataFrame:
    columns = ['Library', 'ModuleName', 'IssueDate', 'Manufacturer', f'{name}Mentioned', 'SunsetDate', "Standard", "Status", "Vendor_url", "Level", "ModuleType"]
    all_df = pd.DataFrame(columns=columns)

    for cert in dataset:
        if cert.pdf_data.keywords and "crypto_library" in cert.pdf_data.keywords and cert.web_data.validation_history:
            list_of_libs = cert.pdf_data.keywords["crypto_library"]
            if name in list_of_libs:
                all_df.loc[len(all_df)] = [name,
                                        cert.web_data.module_name,
                                        cert.web_data.validation_history[0].date if cert.web_data.validation_history else None,
                                        cert.web_data.vendor,
                                        cert.pdf_data.keywords["crypto_library"][name][name],
                                        cert.web_data.date_sunset,
                                        cert.web_data.standard,
                                        cert.web_data.status,
                                        cert.web_data.vendor_url,
                                        cert.web_data.level,
                                        cert.web_data.module_type]

    all_df['IssueDate'] = pd.to_datetime(all_df['IssueDate'])

    all_df['Year'] = all_df['IssueDate'].dt.year

    return all_df
