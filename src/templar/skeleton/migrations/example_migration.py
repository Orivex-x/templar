"""Example migration for new Templar projects."""

from templar.migrations.Migration import Migration


class Migration_001_InitialSetup(Migration):
    """Initial database setup example."""
    
    description = "Initial database setup"
    
    def up(self, db):
        """Create initial tables."""
        # Example: Create a user's table
        # db.execute("""
        #     CREATE TABLE users (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         username VARCHAR(255) NOT NULL UNIQUE,
        #         email VARCHAR(255) NOT NULL UNIQUE,
        #         password_hash VARCHAR(255) NOT NULL,
        #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        #     )
        # """)
        pass
    
    def down(self, db):
        """Rollback."""
        # Example: Drop tables
        # db.execute('DROP TABLE IF EXISTS users')
        pass
