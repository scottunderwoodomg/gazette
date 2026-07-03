live_prompts = {
    "filter": """
        You are a content filter. Below is a list of news articles, each separated by a blank line and starting with a numbered heading like [1], [2], etc.

        I am only interested in articles related to ANY of these topics:
        {interests_list}

        Instructions:
        - Read every article carefully.
        - Return ONLY the full text blocks of articles that are clearly relevant to at least one of the listed topics.
        - Interpret topics broadly and use good judgement — e.g. "schools" should match articles about education, teachers, students, universities, curriculum, etc.
        - Preserve each matching article's text exactly as it appears in the input.
        - Separate each returned article block with a blank line.
        - If NO articles match, respond with exactly: NO_MATCHES

        Do NOT add commentary, headings, or any extra text — only the matching article blocks (or NO_MATCHES).

        --- ARTICLES START ---
        {raw_text}
        --- ARTICLES END ---
    """,
    "prod_filter_backup": """
        You are a content filter. Below is a list of news articles, each separated by a blank line and starting with a numbered heading like [1], [2], etc.

        I am only interested in articles related to ANY of these topics:
        {interests_list}

        Instructions:
        - Read every article carefully.
        - Return ONLY the full text blocks of articles that are clearly relevant to at least one of the listed topics.
        - Interpret topics broadly and use good judgement — e.g. "schools" should match articles about education, teachers, students, universities, curriculum, etc.
        - Preserve each matching article's text exactly as it appears in the input.
        - Separate each returned article block with a blank line.
        - If NO articles match, respond with exactly: NO_MATCHES

        Do NOT add commentary, headings, or any extra text — only the matching article blocks (or NO_MATCHES).

        --- ARTICLES START ---
        {raw_text}
        --- ARTICLES END ---
    """,
    "summary": """
        Below is a collection of RSS news articles with their titles, publication dates, links, and summaries.
        {interest_note}
        Your task:
        1. Identify the major themes or topics across all the articles.
        2. If there are more than 3 major themes or topics related to a given interst use your best judgement to only return 3 themes.
        3. For each theme, write a concise 1–2 sentence description.
        5. Under each theme, produce a concise summary of all the articles relaated to the theme. Favor the existing information and only adjust the summary if sumbsequent articles on the same topic add to it in a meaningful way.  Below the summary, include a row of text links to the articles in question in the following format:
        - Sources: [<name of website from url>](URL), [<name of website from url>](URL)...

        Rules:
        - Do NOT include a generic top-level heading like "Major Themes" or any document or section title.
        - Begin directly with the first ## theme heading.
        - Keep the overall output tight and scannable.
        - Summary should target a 100-120 word limit.
        - There should be no more than 3 topics summarized under each group.
        - If an article fits multiple themes, you may use it as a source for more than one theme/topic summary.
        - Do not invent information; only use what is in the articles provided.
        - Use plain Markdown (headers with ##, bullet points with -).

        --- ARTICLES START ---
        {filtered_text}
        --- ARTICLES END ---
    """,
    "prod_summary_backup": """
        Below is a collection of RSS news articles with their titles, publication dates, links, and summaries.
        {interest_note}
        Your task:
        1. Identify the major themes or topics across all the articles.
        2. For each theme, write a concise 1–2 sentence description.
        3. Under each theme, list the most relevant articles as bullet points using this exact format:
        - [Article Title](URL) — one-sentence relevance note

        Rules:
        - Keep the overall output tight and scannable.
        - Every article bullet must include the hyperlink in Markdown format.
        - If an article fits multiple themes, you may list it under more than one.
        - Do not invent information; only use what is in the articles provided.
        - Use plain Markdown (headers with ##, bullet points with -).

        --- ARTICLES START ---
        {filtered_text}
        --- ARTICLES END ---
    """
}