import datetime
import enum
import uuid

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    event,
)
from sqlalchemy.orm import Session, relationship

from app.database import Base
from app.utils.categorization import get_categories_for_memory

# Import pgvector types for proper vector storage
try:
    from pgvector.sqlalchemy import Vector

    PGVECTOR_AVAILABLE = True
except ImportError:
    # Fallback for systems without pgvector
    PGVECTOR_AVAILABLE = False
    print("Warning: pgvector not installed. Vector operations will use String storage.")


def get_current_utc_time():
    """Get current UTC time"""
    return datetime.datetime.now(datetime.UTC)


class MemoryState(enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"
    deleted = "deleted"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(
        DateTime, default=get_current_utc_time, onupdate=get_current_utc_time
    )

    apps = relationship("App", back_populates="owner")
    memories = relationship("Memory", back_populates="user")


class App(Base):
    __tablename__ = "apps"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    owner_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String)
    metadata_ = Column("metadata", JSON, default=dict)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(
        DateTime, default=get_current_utc_time, onupdate=get_current_utc_time
    )

    owner = relationship("User", back_populates="apps")
    memories = relationship("Memory", back_populates="app")

    __table_args__ = (
        sa.UniqueConstraint("owner_id", "name", name="idx_app_owner_name"),
    )


class Config(Base):
    __tablename__ = "configs"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=get_current_utc_time)
    updated_at = Column(
        DateTime, default=get_current_utc_time, onupdate=get_current_utc_time
    )


class Memory(Base):
    __tablename__ = "memories"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    app_id = Column(UUID, ForeignKey("apps.id"), nullable=False, index=True)
    content = Column(String, nullable=False)
    # Updated to use proper pgvector types for optimal performance
    vector = Column(Vector(1536) if PGVECTOR_AVAILABLE else String, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    state = Column(Enum(MemoryState), default=MemoryState.active, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)
    updated_at = Column(
        DateTime, default=get_current_utc_time, onupdate=get_current_utc_time
    )
    archived_at = Column(DateTime, nullable=True, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    user = relationship("User", back_populates="memories")
    app = relationship("App", back_populates="memories")
    categories = relationship(
        "Category", secondary="memory_categories", back_populates="memories"
    )

    __table_args__ = (
        Index("idx_memory_user_state", "user_id", "state"),
        Index("idx_memory_app_state", "app_id", "state"),
        Index("idx_memory_user_app", "user_id", "app_id"),
        # Vector similarity index will be created by migration script
        # Index('idx_memory_vector_cosine', 'vector', postgresql_using='ivfflat', postgresql_ops={'vector': 'vector_cosine_ops'}) if PGVECTOR_AVAILABLE else None,
    )

    def to_mem0_metadata(self) -> dict:
        """Convert PostgreSQL state to mem0 metadata format"""
        return {
            "state": self.state.value,
            "app_id": str(self.app_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            **self.metadata_,
        }


class Category(Base):
    __tablename__ = "categories"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(String)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.UTC), index=True
    )
    updated_at = Column(
        DateTime, default=get_current_utc_time, onupdate=get_current_utc_time
    )

    memories = relationship(
        "Memory", secondary="memory_categories", back_populates="categories"
    )


memory_categories = Table(
    "memory_categories",
    Base.metadata,
    Column("memory_id", UUID, ForeignKey("memories.id"), primary_key=True, index=True),
    Column(
        "category_id", UUID, ForeignKey("categories.id"), primary_key=True, index=True
    ),
    Index("idx_memory_category", "memory_id", "category_id"),
)


class AccessControl(Base):
    __tablename__ = "access_controls"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    subject_type = Column(String, nullable=False, index=True)
    subject_id = Column(UUID, nullable=True, index=True)
    object_type = Column(String, nullable=False, index=True)
    object_id = Column(UUID, nullable=True, index=True)
    effect = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)

    __table_args__ = (
        Index("idx_access_subject", "subject_type", "subject_id"),
        Index("idx_access_object", "object_type", "object_id"),
    )


class ArchivePolicy(Base):
    __tablename__ = "archive_policies"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    criteria_type = Column(String, nullable=False, index=True)
    criteria_id = Column(UUID, nullable=True, index=True)
    days_to_archive = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=get_current_utc_time, index=True)

    __table_args__ = (Index("idx_policy_criteria", "criteria_type", "criteria_id"),)


class MemoryStatusHistory(Base):
    __tablename__ = "memory_status_history"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    memory_id = Column(UUID, ForeignKey("memories.id"), nullable=False, index=True)
    changed_by = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    old_state = Column(Enum(MemoryState), nullable=False, index=True)
    new_state = Column(Enum(MemoryState), nullable=False, index=True)
    changed_at = Column(DateTime, default=get_current_utc_time, index=True)

    __table_args__ = (
        Index("idx_history_memory_state", "memory_id", "new_state"),
        Index("idx_history_user_time", "changed_by", "changed_at"),
    )


class MemoryAccessLog(Base):
    __tablename__ = "memory_access_logs"
    id = Column(UUID, primary_key=True, default=lambda: uuid.uuid4())
    memory_id = Column(UUID, ForeignKey("memories.id"), nullable=False, index=True)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True, index=True)
    app_id = Column(UUID, ForeignKey("apps.id"), nullable=False, index=True)
    accessed_at = Column(DateTime, default=get_current_utc_time, index=True)
    access_type = Column(String, nullable=False, index=True, default="read")
    metadata_ = Column("metadata", JSON, default=dict)

    # Relationship definitions
    memory = relationship("Memory")
    user = relationship("User")
    app = relationship("App")

    __table_args__ = (
        Index("idx_access_memory_time", "memory_id", "accessed_at"),
        Index("idx_access_app_time", "app_id", "accessed_at"),
        Index("idx_access_user_time", "user_id", "accessed_at"),
    )


def categorize_memory(memory: Memory, db: Session) -> None:
    """Categorize a memory using OpenAI and store the categories in the database."""
    try:
        # Get categories from OpenAI
        categories = get_categories_for_memory(memory.content)

        # Get or create categories in the database
        for category_name in categories:
            category = db.query(Category).filter(Category.name == category_name).first()
            if not category:
                category = Category(
                    name=category_name,
                    description=f"Automatically created category for {category_name}",
                )
                db.add(category)
                db.flush()  # Flush to get the category ID

            # Check if the memory-category association already exists
            existing = db.execute(
                memory_categories.select().where(
                    (memory_categories.c.memory_id == memory.id)
                    & (memory_categories.c.category_id == category.id)
                )
            ).first()

            if not existing:
                # Create the association
                db.execute(
                    memory_categories.insert().values(
                        memory_id=memory.id, category_id=category.id
                    )
                )

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error categorizing memory: {e}")


@event.listens_for(Memory, "after_insert")
def after_memory_insert(mapper, connection, target):
    """Trigger categorization after a memory is inserted."""
    db = Session(bind=connection)
    categorize_memory(target, db)
    db.close()


@event.listens_for(Memory, "after_update")
def after_memory_update(mapper, connection, target):
    """Trigger categorization after a memory is updated."""
    db = Session(bind=connection)
    categorize_memory(target, db)
    db.close()
