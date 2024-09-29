SHARED_TO_ORG_HEADERS = ['Report Id', 'Report Name', 'Shared by', 'Number of hidden columns', 'Unused columns']
NEW_HEADERS = ['Number of hidden columns', 'Unused columns']
REGEX_BI_REQUEST = r"var resolvedClusterUri = 'https://(.*?)';"


class Requests:
    AUTHORITY = "https://login.microsoftonline.com/common"
    CLIENT_ID = "23d8f6bd-1eb0-4cc2-a08c-7bf525c67bcd"
    SCOPE = ['https://analysis.windows.net/powerbi/api/.default openid profile offline_access']
    PUBLISHED_TO_WEB_URL = 'https://api.powerbi.com/v1.0/myorg/admin/widelySharedArtifacts/publishedToWeb'
    SHARED_TO_ORG_URL = 'https://api.powerbi.com/v1.0/myorg/admin/widelySharedArtifacts/linksSharedToWholeOrganization'
    PUSH_ACCESS_URL = 'https://{}/metadata/access/reports/{}/pushaccess?forceRefreshGroups=true'
    EXPLORATION_URL = 'https://{}/explore/reports/{}/exploration'
    CONCEPTUAL_SCHEMA_URL = 'https://{}/explore/conceptualschema'


class PublicRequests(Requests):
    EXPLORATION_URL = 'https://{}/public/reports/{}/modelsAndExploration?preferReadOnlySession=true'
    CONCEPTUAL_SCHEMA_URL = 'https://{}/public/reports/conceptualschema'


class ResponseKeys:
    ACCESS_TOKEN = "access_token"
    ARTIFACT_ID = 'artifactId'
    ARTIFACT_ACCESS_ENTITIES = 'ArtifactAccessEntities'
    REGION = '@odata.context'
    REPORT = 'report'
    OWNER_INFO = 'ownerInfo'
    FIRST_NAME = 'givenName'
    LAST_NAME = 'familyName'
    DISPLAY_NAME = 'displayName'
    SHARER = 'sharer'
    UNKNOWN_REPORT = 'Unknown Report'
    UNKNOWN_SHARER = 'Unknown Sharer'
    TABLE = 'table'
    COLUMN = 'column'
    UNUSED = 'unused'
    MODELS = 'models'
    ID = 'id'
    ENTITY_KEY = 'entityKey'
    RELATED_ENTITY_KEY = 'relatedEntityKeys'
    TYPE = 'type'


class ExplorationRequestError(Exception):
    pass
