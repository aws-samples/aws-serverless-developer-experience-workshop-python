// The workflows pass the PR title and body through `jq -c`, so they arrive as JSON
// strings: wrapped in quotes, with line breaks as the two characters "\n". Decode them
// so the scripts match against the text the author wrote. Plain text is used as-is.
function decode(value) {
    if (!value) return "";
    try {
        const decoded = JSON.parse(value);
        return typeof decoded === "string" ? decoded : value;
    } catch {
        return value;
    }
}

module.exports = Object.freeze({
    /** @type {string} */
    // Values: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request
    "PR_ACTION": process.env.PR_ACTION?.replace(/"/g, '') || "",

    /** @type {string} */
    "PR_AUTHOR": process.env.PR_AUTHOR?.replace(/"/g, '') || "",

    /** @type {string} */
    "PR_BODY": decode(process.env.PR_BODY),

    /** @type {string} */
    "PR_TITLE": decode(process.env.PR_TITLE),

    /** @type {number} */
    "PR_NUMBER": process.env.PR_NUMBER || 0,

    /** @type {string} */
    "PR_IS_MERGED": process.env.PR_IS_MERGED || "false",

    /** @type {string} */
    "LABEL_BLOCK": "do-not-merge",

    /** @type {string} */
    "LABEL_BLOCK_REASON": "need-issue",

    /** @type {string} */
    "LABEL_BLOCK_MISSING_LICENSE_AGREEMENT": "need-license-agreement-acknowledge",

    /** @type {string} */
    "LABEL_PENDING_RELEASE": "pending-release",

    /** @type {string} */
    // Team shared by all four workshop repositories; mentioned when a merged PR names no issue.
    "HANDLE_MAINTAINERS_TEAM": "@aws-samples/aws-serverless-developer-experience-workshop",

    /** @type {string[]} */
    "IGNORE_AUTHORS": ["dependabot[bot]", "markdownify[bot]"],

});
