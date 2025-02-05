from langchain_text_splitters import MarkdownHeaderTextSplitter


class MdProcessor:
    """
    class MdProcessor
    A utility class for processing Markdown data.

    This class provides static methods to filter, split, and process Markdown content,
    particularly focused on Code4rena contest reports.

    The MdProcessor class contains static methods that can be used to:
    - Filter Markdown data based on specific topics
    - Extract issue descriptions and impacts from Markdown data
    - Split Markdown text into structured segments based on headers

    This class is designed to work with Markdown data structured in a specific format,
    typically used in Code4rena contest reports.

    Methods:
        filter_topic(md_data: list) -> list:
            Filters the input Markdown data to include only "Risk Findings" topics.

        filter_issue(md_data: list) -> list:
            Extracts the description and impact from a given Markdown data segment.

        split(markdown_text: list, headers: list, strip_headers: bool) -> list:
            Splits the Markdown text into segments based on specified headers.

    """

    @staticmethod
    def filter_topic(md_data: list) -> list:
        filtered = [
            i.page_content
            for i in md_data
            if "Topic" in i.metadata
            and (
                "High Risk Findings" in i.metadata["Topic"]
                or "Medium Risk Findings" in i.metadata["Topic"]
            )
        ]
        return filtered

    @staticmethod
    def filter_issue(md_data: list) -> list:
        description = md_data[0].page_content
        impact = None
        poc = None
        if len(md_data) == 1:
            return [description, None, None]

        for i in md_data[1:]:
            if "Details" in i.metadata and "Impact" in i.metadata["Details"]:
                impact = i.page_content
            if "Details" in i.metadata and "Proof of Concept" in i.metadata["Details"]:
                poc = i.page_content
        return [description, impact, poc]

    @staticmethod
    def split(
        markdown_text: list,
        headers: list = [("#", "Topic"), ("##", "Item")],
        strip_headers: bool = False,
    ) -> list:
        md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers, strip_headers=strip_headers
        )
        md_header_splits = md_splitter.split_text(markdown_text)
        return md_header_splits
