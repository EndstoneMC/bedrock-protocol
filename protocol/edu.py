package = "bedrock.protocol"


# BDS declares linkUri before buttonName; the wire writes buttonName first.
class EduSharedUriResource:
    button_name: str
    link_uri: str
