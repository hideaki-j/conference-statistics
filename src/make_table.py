import pandas as pd
import os
import json

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
                    if j + 3 < len(lines):
                        num_str = lines[j + 3].strip()  # Number is three lines after "Pages " or "Page "
                        
                        # If num_str is empty, check j + 4
                        if not num_str and j + 4 < len(lines):
                            num_str = lines[j + 4].strip()
                        
                        # If num_str is still empty, check j + 5
                        if not num_str and j + 5 < len(lines):
                            num_str = lines[j + 5].strip()
                        
                        if len(num_str) > 1:  # Ensure there are enough digits for citation and downloads
                            citations = int(num_str[0])  # First digit for citations
                            downloads = int(num_str[1:].replace(',', ''))  # Remaining digits for downloads
                            # Article type logic
                            if lines[j-3].strip().startswith("Best"):
                                if lines[j-4].strip() == "Open Access":
                                    article_type = lines[j-5].strip()  # Check five lines before if "Best" and "Open Access"
                                else:
                                    article_type = lines[j-4].strip()  # Check four lines before if only "Best"
                            elif lines[j-3].strip() == "Open Access":
                                article_type = lines[j-4].strip()  # Check four lines before if "Open Access"
                            else:
                                article_type = lines[j-3].strip()  # Otherwise, three lines before
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

# Read the file content: this is the copied and pasted text from the ACM website
file_path = 'data/241015/241015 Proceedings of the 47th International ACM SIGIR Conference.txt'
with open(file_path, 'r', encoding='utf-8') as file:
    file_content = file.read()

# Apply the function to the file content
df_results, match_count = get_info_from_copy_and_pasted_text(file_content)

# Ensure the './results' directory exists
os.makedirs('./results', exist_ok=True)

# Save the DataFrame as a CSV file
csv_output_path = '../results/sigir24_statistics.csv'
df_results.to_csv(csv_output_path, index=False)

# Save the data as a JavaScript file
js_output_path = '../results/sigir24_statistics.js'
js_content = dataframe_to_js_dict(df_results)
with open(js_output_path, 'w', encoding='utf-8') as js_file:
    js_file.write(js_content)

print(f"Data has been processed and saved to {csv_output_path}")
print(f"JavaScript data has been saved to {js_output_path}")
print(f"Total matches found: {match_count}")
print(f"Total rows in the DataFrame: {len(df_results)}")
print(f"Columns in the DataFrame: {', '.join(df_results.columns)}")
