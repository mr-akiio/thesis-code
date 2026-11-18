from sec_certs.dataset.cc import CCDataset
from sec_certs.dataset.fips import FIPSDataset
import re

import pandas as pd
from .manufacturer_cleanup import unify_manufacturer, process_manufacturer_names
from .unification_dictionaries import vendor_country

def get_cc_library_mentions(dataset: CCDataset, name: str) -> pd.DataFrame:
    columns = ['Library', 'Manufacturer', 'IssueDate', 'SunsetDate', f"{name}MentionedReport", f"{name}MentionedTarget", 'Country', 'Category']


    result = pd.DataFrame(columns=columns)

    for cert in dataset:
        if "Network" in cert.category:
            category = "Network Devices and Systems"
        elif "Smart Card" in cert.category:
            category = "Smart Cards"
        else:
            category = cert.category
        if cert.manufacturer in [None, "[email protected]"]:
            continue
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
                                       category
                                       ]

    return result

def get_fips_library_mentions(dataset: FIPSDataset, name: str) -> pd.DataFrame:
    columns = ['Library', 'ModuleName', 'IssueDate', 'Manufacturer', f'{name}Mentioned', 'SunsetDate', "Standard", "Status", "Vendor_url", "Level", "ModuleType"]
    all_df = pd.DataFrame(columns=columns)

    for cert in dataset:
        if "email" in cert.web_data.vendor.lower():
            continue
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


# Keyword categories that hold algorithm names
ALGORITHM_CATEGORIES = ['symmetric_crypto', 'asymmetric_crypto', 'hash_function', 'pq_crypto', 'ecc_curve']


def collapse_cc_category(category: str) -> str:
    if "Network" in category:
        return "Network Devices and Systems"
    if "Smart Card" in category:
        return "Smart Cards"
    return category


def _walk_algorithms(name, node):
    # Keyword dicts nest 2 or 3 levels deep, even within one category
    # (e.g. RSA -> matches, but ECC -> ECDSA -> matches). An algorithm is a
    # node whose values are raw match counts; yield (algorithm, total count).
    count = sum(v for v in node.values() if isinstance(v, int))
    if count:
        yield name, count
    for key, child in node.items():
        if isinstance(child, dict):
            yield from _walk_algorithms(key, child)


# Algorithm labels whose keyword matches are (nearly) always something else, checked by
# sampling the matched text in the certificate artifacts:
FALSE_POSITIVE_ALGORITHMS = {
    'E2',        # interface / model names (IMS-SM-E2, PSI-E2), URL-encoded bytes (%E2)
    'HPC',       # German Health Professional Card
    'JH',        # author initials in the RFC 4493 citation
    'Skinny',    # Cisco Skinny Client Control Protocol (SCCP)
    'MARS',      # Cisco Security MARS appliance
    'MAGENTA',   # status LED colour
    'Rainbow',   # Rainbow Technologies (vendor)
    'Rabbit',    # a program name
    'Saber',     # Motorola Astro Saber radio
    'Falcon',    # product names (CrowdStrike Falcon, AMD Merlin Falcon, ...)
    'AEGIS',     # Motorola AEGIS voice protocol, Apricorn Aegis drives
    'Lucifer',   # only the historical note that DES was first called Lucifer
    'Elephant',  # BitLocker's Elephant Diffuser, not the Elephant lightweight cipher
}

# Labels that are genuine in most certificates but share a name with something else.
# A mention only counts if the certificate text has an occurrence outside the excluded
# context. Values: (pattern for the algorithm, pattern that marks a false context within
# CONTEXT_WINDOW characters).
CONTEXT_CHECKED_ALGORITHMS = {
    # Korean block cipher vs. DRBG seed / DSA domain parameter SEED
    'SEED': (re.compile(r'\bSEED\b'),
             re.compile(r'pgen|domain param|counter|D?RBG|D?RNG|entropy|nonce|SEED[\s-]*(key|len|value)',
                        re.IGNORECASE)),
    # CAST-128/256 cipher vs. FIPS "Cryptographic Algorithm Self-Test" (CAST): self-test
    # wording, FIPS 140-3 self-test table columns, and "<algorithm> CAST" (e.g. "AES GCM
    # Encrypt CAST", "HMAC-SHA-256 CAST"; a comma-separated cipher list does not match).
    'CAST': (re.compile(r'\bCAST(?:[- ]?(?:5|6|128|256))?\b'),
             re.compile(r'self[- ]?test|\btests?\b|\bKAT\b|known answer|\(CAST\)|\bCASTs\b'
                        r'|\bfail|fault|status|on demand|conditional|pre-operational|power[- ]?up|periodic|performed|entropy|\bFD\b'
                        r'|(?:AES|SHA|HMAC|DRBG|KDF|DSA|RSA|KAS|KTS|ML-\w+|GCM|CMAC|Encrypt|Decrypt|Sign|Verify)'
                        r'[\w/-]*\s+CAST\b',
                        re.IGNORECASE)),
}
CONTEXT_WINDOW = 50


def _genuine_occurrences(algorithm, text) -> int:
    pattern, false_context = CONTEXT_CHECKED_ALGORITHMS[algorithm]
    count = 0
    for match in pattern.finditer(text):
        if match.group(0) != 'CAST' and algorithm == 'CAST':
            count += 1  # CAST5, CAST-128, ... always mean the cipher
            continue
        window = text[max(0, match.start() - CONTEXT_WINDOW):match.end() + CONTEXT_WINDOW]
        if not false_context.search(window):
            count += 1
    return count


def read_text(get_path) -> str | None:
    """Read a certificate text artifact; get_path is a callable because txt_path can raise."""
    try:
        path = get_path()
        return path.read_text(errors='ignore') if path and path.exists() else None
    except (ValueError, OSError):
        return None


def extract_algorithms(keywords, categories=ALGORITHM_CATEGORIES, get_text=None) -> dict:
    """Map (keyword category, family, algorithm) -> match count for one keyword dict.

    Algorithms in FALSE_POSITIVE_ALGORITHMS are dropped. Algorithms in
    CONTEXT_CHECKED_ALGORITHMS are recounted in the document text returned by get_text()
    (read lazily, only when needed); if the text is unavailable, the keyword count is kept.
    """
    result = {}
    if not keywords:
        return result
    text = None
    for category in categories:
        for family, node in (keywords.get(category) or {}).items():
            if not isinstance(node, dict):
                continue
            for algorithm, count in _walk_algorithms(family, node):
                if algorithm in FALSE_POSITIVE_ALGORITHMS:
                    continue
                if algorithm in CONTEXT_CHECKED_ALGORITHMS and get_text is not None:
                    if text is None:
                        text = get_text() or ''
                    if text:
                        count = _genuine_occurrences(algorithm, text)
                        if not count:
                            continue
                key = (category, family, algorithm)
                result[key] = result.get(key, 0) + count
    return result


def get_cc_algorithm_mentions(dataset: CCDataset, categories=ALGORITHM_CATEGORIES):
    """Return (certs, mentions) DataFrames for country-level algorithm analysis.

    certs has one row per certificate with at least one keyword dict (the denominator for shares).
    mentions has one row per (certificate, algorithm), with match counts from the report and the ST.
    Country is the CC scheme. Unlike get_cc_library_mentions, certificates with an obfuscated
    or missing manufacturer are kept, because the country does not depend on it.
    """
    cert_rows, mention_rows = [], []
    for cert in dataset:
        report_kw = cert.pdf_data.report_keywords
        target_kw = cert.pdf_data.st_keywords
        if not report_kw and not target_kw:
            continue
        cert_rows.append({
            'Dgst': cert.dgst,
            'Country': cert.scheme,
            'Category': collapse_cc_category(cert.category),
            'Manufacturer': cert.manufacturer,
            'IssueDate': cert.not_valid_before,
            'Status': cert.status,
        })
        report_algs = extract_algorithms(report_kw, categories,
                                         get_text=lambda: read_text(lambda: cert.state.report.txt_path))
        target_algs = extract_algorithms(target_kw, categories,
                                         get_text=lambda: read_text(lambda: cert.state.st.txt_path))
        for key in report_algs.keys() | target_algs.keys():
            mention_rows.append({
                'Dgst': cert.dgst,
                'KeywordCategory': key[0],
                'Family': key[1],
                'Algorithm': key[2],
                'ReportCount': report_algs.get(key, 0),
                'TargetCount': target_algs.get(key, 0),
            })

    certs = pd.DataFrame(cert_rows)
    certs['IssueDate'] = pd.to_datetime(certs['IssueDate'])
    certs['Year'] = certs['IssueDate'].dt.year
    mentions = pd.DataFrame(mention_rows).merge(certs, on='Dgst')
    return certs, mentions


def get_fips_algorithm_mentions(dataset: FIPSDataset, categories=ALGORITHM_CATEGORIES):
    """Return (certs, mentions) DataFrames for country-level algorithm analysis.

    Country comes from vendor_country, looked up by unified vendor name ('Unknown' if unmapped).
    Like get_fips_library_mentions, vendors obfuscated as "email" are skipped.
    """
    cert_rows, mention_rows = [], []
    for cert in dataset:
        vendor = cert.web_data.vendor or ''
        if "email" in vendor.lower() or not cert.pdf_data.keywords:
            continue
        history = cert.web_data.validation_history
        cert_rows.append({
            'Dgst': cert.dgst,
            'Manufacturer': vendor,
            'IssueDate': history[0].date if history else None,
            'Standard': cert.web_data.standard,
            'Status': cert.web_data.status,
        })
        algorithms = extract_algorithms(cert.pdf_data.keywords, categories,
                                        get_text=lambda: read_text(lambda: cert.state.policy.txt_path))
        for key, count in algorithms.items():
            mention_rows.append({
                'Dgst': cert.dgst,
                'KeywordCategory': key[0],
                'Family': key[1],
                'Algorithm': key[2],
                'Count': count,
            })

    certs = process_manufacturer_names(pd.DataFrame(cert_rows), 'Manufacturer')
    certs['Country'] = certs['Manufacturer'].map(vendor_country).fillna('Unknown')
    certs['IssueDate'] = pd.to_datetime(certs['IssueDate'])
    certs['Year'] = certs['IssueDate'].dt.year
    mentions = pd.DataFrame(mention_rows).merge(certs, on='Dgst')
    return certs, mentions
