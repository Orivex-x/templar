from types import SimpleNamespace

from templar.core.deployment.SshProvider import SSHProvider
from templar.db.providers.SQLite import SQLiteProvider


def test_sqlite_provider_supports_a_database_file_in_the_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    database = SQLiteProvider("sqlite:///templar.db")

    database.connect()

    try:
        database.execute("CREATE TABLE example (id INTEGER PRIMARY KEY)")
    finally:
        database.close()

    assert (tmp_path / "templar.db").is_file()


def test_ssh_deployment_uses_portable_openssh_commands(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(
        "templar.core.deployment.SshProvider.shutil.which",
        lambda name: f"/tools/{name}",
    )
    monkeypatch.setattr(
        "templar.core.deployment.SshProvider.subprocess.run",
        lambda command, check=False: commands.append(command) or SimpleNamespace(returncode=0),
    )

    provider = SSHProvider()
    provider.deploy(
        str(tmp_path),
        {
            "host": "example.test",
            "user": "deploy",
            "dest": "/srv/app",
            "ssh_key": "key.pem",
            "remote_commands": ["python -m pip install -r requirements.txt"],
        },
    )

    assert commands[0][:4] == ["scp", "-i", "key.pem", "-r"]
    assert commands[0][-1] == "deploy@example.test:/srv/app"
    assert commands[1][:4] == ["ssh", "-i", "key.pem", "deploy@example.test"]
