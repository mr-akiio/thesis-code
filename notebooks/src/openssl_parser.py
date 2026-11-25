import urllib.request
import json
import re
import os

def parse_openssl_docs():
    url = "https://docs.openssl.org/3.3/man3/"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
            # The docs have a table format: <tr><td><a href="...">name</a></td><td>description</td></tr>
            # Extract the text inside the <a> tag which corresponds to the library/function name.
            pattern = r"<td><a\s+href=[^>]+>([^<]+)</a>"
            matches = re.findall(pattern, html)
            
            # Clean up and remove duplicates if any (while preserving order)
            names = []
            seen = set()
            for m in matches:
                name = m.strip()
                if name and name not in seen:
                    names.append(name)
                    seen.add(name)
            
            # Save to json file in the same directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_file = os.path.join(script_dir, "openssl_man3.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(names, f, indent=4)
            
            print(f"Extracted {len(names)} library names and saved to {output_file}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parse_openssl_docs()
