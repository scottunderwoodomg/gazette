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
    "summary": """
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