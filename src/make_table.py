import pandas as pd
import os
import json
import argparse  # Add this import
import re


def split_citations_and_downloads(num_str, max_download=20000):
    digits = num_str.replace(',', '')
    if not digits or not digits.isdigit():
        return None, None

    candidates = []
    max_download_len = min(5, len(digits))

    for download_len in range(1, max_download_len + 1):
        download_digits = digits[-download_len:]
        citation_digits = digits[:-download_len]

        if not citation_digits:
            continue

        if len(citation_digits) > 1 and citation_digits[0] == '0':
            continue

        download_val = int(download_digits)
        if download_val > max_download:
            continue

        formatted_download = f"{download_val:,}"
        if citation_digits + formatted_download == num_str:
            citation_val = int(citation_digits)
            candidates.append((citation_val, download_val, download_len))

    if not candidates:
        return None, int(digits)

    def prefer(cands, predicate):
        filtered = [c for c in cands if predicate(c)]
        return filtered if filtered else cands

    candidates = prefer(candidates, lambda c: c[0] <= 500)
    candidates = prefer(candidates, lambda c: c[1] >= 100)
    candidates = prefer(candidates, lambda c: c[1] <= 10000)

    candidates.sort(key=lambda c: (c[1], -c[0]))
    citation_val, download_val, _ = candidates[0]
    return citation_val, download_val


# Update the function to ensure that no lines are omitted, including those without "Pages" or "Page"
def get_info_from_copy_and_pasted_text(text):
    lines = text.splitlines()
    results = []
    match_count = 0  # Initialize a counter to track matches
    
    for i in range(len(lines)):
        if lines[i].startswith("Author Picture"):
            match_count += 1  # Increment the counter when a match is found
            title = lines[i-1].strip()  # Title is one line before "Author Picture"
            citations = None
            downloads = None
            article_type = ''
            
            # Now check for "Pages" or "Page"
            for j in range(i, len(lines)):
                if lines[j].startswith("Pages ") or lines[j].startswith("Page "):
                    num_str = ""
                    k = j + 1
                    while k < len(lines):
                        candidate = lines[k].strip()
                        if candidate and re.fullmatch(r"[0-9,]+", candidate):
                            num_str = candidate
                            break
                        k += 1

                    if num_str:
                        citations, downloads = split_citations_and_downloads(num_str)
                        if downloads is None:
                            downloads = int(num_str.replace(',', ''))

                        if j - 3 >= 0 and lines[j-3].strip().startswith("Best"):
                            if j - 4 >= 0 and lines[j-4].strip() == "Open Access":
                                if j - 5 >= 0:
                                    article_type = lines[j-5].strip()
                            else:
                                article_type = lines[j-4].strip() if j - 4 >= 0 else ''
                        elif j - 3 >= 0 and lines[j-3].strip() == "Open Access":
                            article_type = lines[j-4].strip() if j - 4 >= 0 else ''
                        else:
                            article_type = lines[j-3].strip() if j - 3 >= 0 else ''
                    break
            
            results.append({
                "title": title,
                "citations": citations,
                "downloads": downloads,
                "article_type": article_type
            })

    # Convert to DataFrame for sorting
    df_results = pd.DataFrame(results)
    
    # Sort by 'downloads' in descending order, NaN entries will be at the bottom
    df_results_sorted = df_results.sort_values(by="downloads", ascending=False, na_position='last')

    # Calculate 'top %' for non-NaN download values
    total_articles = len(df_results_sorted)
    non_nan_downloads = df_results_sorted['downloads'].notna()
    df_results_sorted.loc[non_nan_downloads, 'top %'] = (df_results_sorted.loc[non_nan_downloads, 'downloads'].rank(method='min', ascending=False) / non_nan_downloads.sum() * 100).round(2)
    
    # Set 'top %' to NaN for articles with NaN download values
    df_results_sorted.loc[~non_nan_downloads, 'top %'] = pd.NA

    # Calculate 'rank' for non-NaN download values
    df_results_sorted.loc[non_nan_downloads, 'rank'] = df_results_sorted.loc[non_nan_downloads, 'downloads'].rank(method='min', ascending=False).astype(int)
    
    # Set 'rank' to -1 (special value) for articles with NaN download values
    df_results_sorted.loc[~non_nan_downloads, 'rank'] = -1

    # Convert 'rank' column to integer type
    df_results_sorted['rank'] = df_results_sorted['rank'].astype(int)

    # Reorder columns to make 'rank' the first column
    columns_order = ['rank'] + [col for col in df_results_sorted.columns if col != 'rank']
    df_results_sorted = df_results_sorted[columns_order]

    return df_results_sorted, match_count

def dataframe_to_js_dict(df):
    """Convert DataFrame to a JavaScript dictionary string."""
    # Convert DataFrame to dictionary
    data_dict = df.to_dict(orient='records')
    
    # Convert to JSON string
    json_str = json.dumps(data_dict, indent=2)
    
    # Create JavaScript variable assignment
    js_string = f"const sigirData = {json_str};"
    
    return js_string

# Update this block near the top of the script, after imports
parser = argparse.ArgumentParser(description='Process SIGIR conference data.')
parser.add_argument('--file_path', type=str, help='Path to the input text file', required=True)
args = parser.parse_args()

# Use args.file_path instead of args.file_path in the rest of your script
file_path = args.file_path

# Read the file content: this is the copied and pasted text from the ACM website
with open(file_path, 'r', encoding='utf-8') as file:
    file_content = file.read()

# Apply the function to the file content
df_results, match_count = get_info_from_copy_and_pasted_text(file_content)

# Ensure the results directory exists relative to the project root
src_dir = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.join(os.path.dirname(src_dir), 'results')
os.makedirs(results_dir, exist_ok=True)

# Save the DataFrame as a CSV file
csv_output_path = os.path.join(results_dir, 'sigir24_statistics.csv')
df_results.to_csv(csv_output_path, index=False)

# Save the data as a JavaScript file
js_output_path = os.path.join(results_dir, 'sigir24_statistics.js')
js_content = dataframe_to_js_dict(df_results)
with open(js_output_path, 'w', encoding='utf-8') as js_file:
    js_file.write(js_content)

print(f"Data has been processed and saved to {csv_output_path}")
print(f"JavaScript data has been saved to {js_output_path}")
print(f"Total matches found: {match_count}")
print(f"Total rows in the DataFrame: {len(df_results)}")
print(f"Columns in the DataFrame: {', '.join(df_results.columns)}")
