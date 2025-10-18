"""Gadgets exposed by the sample reporter plugin."""

from datetime import datetime


def provide_gadgets(base_url: str):
    """Return a list of gadget dictionaries for the gadget hub."""

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    quick_stats_html = f"""
        <strong>Latest coverage snapshot</strong>
        <ul>
            <li>Last sync: <b>{generated_at}</b></li>
            <li>Targets monitored: <b>5</b></li>
            <li>Alerts triggered: <b>0</b></li>
        </ul>
    """

    public_key_block = """
        <p>Current verification key:</p>
        <pre>ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOpSampleKeyForDemoOnly sample@reporter</pre>
    """

    return [
        {
            "id": "sample-reporter-stats",
            "title": "Sample Reporter snapshot",
            "description": "A quick look at the latest monitoring statistics.",
            "content_html": quick_stats_html,
            "order": 10,
        },
        {
            "id": "sample-reporter-key",
            "title": "Public verification key",
            "description": "Share this key with clients that need to validate your reports.",
            "content_html": public_key_block,
            "download": {
                "label": "Download CSV report",
                "url": f"{base_url}/sample-report",
            },
            "order": 20,
        },
    ]
