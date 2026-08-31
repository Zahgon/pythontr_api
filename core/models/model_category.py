from app.extensions import db

from .base import SaveMixin, now, unique_slug


class Category(db.Model, SaveMixin):
    __tablename__ = 'core_category'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)
    name = db.Column(db.String(255), nullable=False, unique=True)
    title = db.Column(db.String(255), nullable=False, unique=True,
                      default='')
    title_h1 = db.Column(db.String(255), nullable=False, default='')
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    short_name = db.Column(db.String(100), nullable=False, unique=True)
    parent_category_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_category.id', ondelete='SET NULL'),
        nullable=True,
    )
    slug = db.Column(db.String(150), nullable=False, unique=True)
    sort = db.Column(db.SmallInteger, nullable=True, default=0)
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='SET NULL'),
        nullable=True,
    )

    parent_category = db.relationship(
        'Category', remote_side=[id], backref='category_set',
    )
    user = db.relationship('User')

    @property
    def pk(self):
        return self.id

    def get_slug(self):
        return unique_slug(Category, Category.slug, self.name)

    def save(self, *args, **kwargs):
        if not self.title_h1:
            self.title_h1 = self.title

        self.updated_at = now()
        if self.created_at is None:
            self.created_at = self.updated_at
        self.slug = self.get_slug()

        return super(Category, self).save()

    @property
    def full_category_name(self):
        return self.__str__()

    def __str__(self):
        full_path = [self.name]
        k = self.parent_category
        while k is not None:
            full_path.append(k.name)
            k = k.parent_category

        full_path = ' / '.join(full_path[::-1])

        return full_path
