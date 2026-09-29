from anthropic.types import Message


def response_text(response: Message) -> str:
    """
    Joins the text blocks of a Claude response.
    The response can also contain thinking blocks, so content[0] is not always text.
    """
    if response.stop_reason == "refusal":
        return "The model declined to answer this request."
    return "".join(block.text for block in response.content if block.type == "text")
