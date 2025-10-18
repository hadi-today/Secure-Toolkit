from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class ManagedList(db.Model):
    __tablename__ = 'managed_lists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)

    items = db.relationship(
        'ListItem',
        backref='managed_list',
        cascade='all, delete-orphan',
        lazy=True,
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'item_count': len(self.items),
        }


class ListItem(db.Model):
    __tablename__ = 'list_items'

    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(
        db.Integer,
        db.ForeignKey('managed_lists.id'),
        nullable=False,
    )
    key = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(500), nullable=True)
    is_enabled = db.Column(db.Boolean, default=True, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'list_id': self.list_id,
            'key': self.key,
            'value': self.value,
            'is_enabled': self.is_enabled,
        }


def init_app_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print('Database initialized and tables created.')
