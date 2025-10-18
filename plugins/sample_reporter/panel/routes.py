from flask import Blueprint, Response, render_template

from plugins.web_panel.server.database import ManagedList, db
from plugins.web_panel.server.database import ListItem
from plugins.web_panel.server.web_auth import token_required


reporter_bp = Blueprint(
    'reporter',
    __name__,
    template_folder='templates',
    static_folder='static',
)


@reporter_bp.route('/')
@token_required
def report_page():
    list_name = 'Monitored Sites'
    created_list = False
    error_message = None
    snapshot = []

    try:
        target_list = ManagedList.query.filter_by(name=list_name).first()

        if not target_list:
            target_list, created_list = _create_sample_list(list_name)

        if target_list:
            snapshot = [
                {
                    'id': item.id,
                    'key': item.key,
                    'value': item.value,
                    'is_enabled': item.is_enabled,
                }
                for item in target_list.items
            ]
        else:
            error_message = (
                f"The list '{list_name}' could not be created automatically."
            )
    except Exception as error:
        error_message = f'An error occurred while loading data: {error}'

    return render_template(
        'reporter.html',
        list_name=list_name,
        created_list=created_list,
        snapshot=snapshot,
        error_message=error_message,
    )


@reporter_bp.route('/sample-report')
@token_required
def download_sample_report():
    csv_content = (
        'label,value\n'
        'example.com,Uptime OK\n'
        'contoso.net,SSL expires soon\n'
        'fabrikam.org,Disabled'
    )
    response = Response(csv_content, mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename="sample_report.csv"'
    return response


def _create_sample_list(list_name: str):
    try:
        sample_list = ManagedList(
            name=list_name,
            description='Sample list created by Sample Reporter',
        )
        db.session.add(sample_list)
        db.session.flush()

        sample_items = [
            ListItem(
                managed_list=sample_list,
                key='example.com',
                value='Uptime OK',
                is_enabled=True,
            ),
            ListItem(
                managed_list=sample_list,
                key='contoso.net',
                value='SSL expires soon',
                is_enabled=True,
            ),
            ListItem(
                managed_list=sample_list,
                key='fabrikam.org',
                value='Disabled for maintenance',
                is_enabled=False,
            ),
        ]
        db.session.add_all(sample_items)
        db.session.commit()
        return sample_list, True
    except Exception:
        db.session.rollback()
        return None, False

