from collections.abc import ByteString, Callable
import configparser
import logging
from pathlib import Path

# initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# log to the console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


def wrap_read_callable_point(src_string: ByteString) -> Callable[int, str]:
    def read_callable_byte_offset(byte_offset, _):
        return src_string[byte_offset : byte_offset + 1]

    return read_callable_byte_offset


def locate_git_root(src_dir: Path) -> Path | None:
    """Traverse upwards to find git root."""
    current = src_dir.resolve()
    parents = list(current.parents)
    parents.append(current)
    for parent in parents:
        if (parent / ".git").exists() and (parent / ".git").is_dir():
            return parent
    return None


def get_remote_url(git_root: Path, remote_name: str = "origin") -> str | None:
    """Get remote url from .git/config."""
    config_path = git_root / ".git" / "config"
    if not config_path.exists():
        logging.warning(f"{config_path} does not exist")
        return None

    config = configparser.ConfigParser()
    config.read(config_path)
    section = f'remote "{remote_name}"'
    if section in config and "url" in config[section]:
        url: str = config[section]["url"]
        return url
    logger.warning(f"remote-url is not found in {config_path}")
    return None


def get_current_rev(git_root: Path) -> str | None:
    """Get current commit rev from .git/HEAD."""
    head_path = git_root / ".git" / "HEAD"
    if not head_path.exists():
        logging.warning(f"{head_path} does not exist")
        return None
    head_content = head_path.read_text().strip()
    if not head_content.startswith("ref: "):
        logging.warning(f"Expect starting with 'ref: ' in {head_path}")
        return None

    ref_path = git_root / ".git" / head_content.split(":", 1)[1].strip()
    if not ref_path.exists():
        logging.warning(f"{ref_path} does not exist")
        return None
    return ref_path.read_text().strip()
