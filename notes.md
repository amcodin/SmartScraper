### Maybe change the chunk size, controlF TODO
    chunks = split_text_into_chunks(
        text=docs_transformed.page_content,
        chunk_size=self.chunk_size - 250,
    )