// Dynamic configuration for RunPod proxy
const getApiUrl = (port) => {
    if (window.location.hostname.includes("proxy.runpod.net")) {
        return "https://" + window.location.hostname.replace("-8000", "-" + port);
    } else {
        return "http://localhost:" + port;
    }
};

const CONFIG = {
    API_BASE: getApiUrl("8003"),
    NATIVE_SEARCH_BASE: getApiUrl("8003"),
    DOCUMENT_SEARCH_BASE: getApiUrl("8001"),
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000
};
