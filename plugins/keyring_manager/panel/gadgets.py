"""Dashboard gadgets exposed by the keyring manager plugin."""


def provide_gadgets(base_url: str):
    """Return gadget descriptors for the keyring manager dashboard widgets."""

    summary_html = f"""
        <div class=\"keyring-gadget\" data-gadget-type=\"keyring-summary\" data-endpoint=\"{base_url}/api/summary\">
            <p class=\"keyring-gadget__status\" data-role=\"status\">Sign in to load key totals.</p>
            <dl class=\"keyring-gadget__counts\" hidden>
                <div class=\"keyring-gadget__row\">
                    <dt>My public keys</dt>
                    <dd data-role=\"my-count\">0</dd>
                </div>
                <div class=\"keyring-gadget__row\">
                    <dt>Contacts' keys</dt>
                    <dd data-role=\"contact-count\">0</dd>
                </div>
                <div class=\"keyring-gadget__row\">
                    <dt>Total keys</dt>
                    <dd data-role=\"total-count\">0</dd>
                </div>
            </dl>
            <a class=\"keyring-gadget__link\" href=\"{base_url}\" target=\"_blank\" rel=\"noopener\">Open keyring manager</a>
        </div>
    """

    return [
        {
            "id": "keyring-manager-summary",
            "title": "Keyring overview",
            "description": "Quick look at how many public keys you and your contacts have stored.",
            "content_html": summary_html,
            "order": 15,
        }
    ]