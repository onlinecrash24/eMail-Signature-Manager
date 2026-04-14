import os
import re


def parse_smb_path(smb_path):
    """Parse an SMB path like \\\\server\\share\\path into components.

    Args:
        smb_path: UNC path string, e.g. \\\\server\\share\\subfolder\\path

    Returns:
        Tuple of (server, share, remote_path) where remote_path may be empty.

    Raises:
        ValueError: If the path cannot be parsed.
    """
    # Normalize backslashes to forward slashes
    normalized = smb_path.replace('\\', '/')

    # Strip leading slashes
    normalized = normalized.lstrip('/')

    parts = normalized.split('/')
    if len(parts) < 2:
        raise ValueError(
            f'Ungültiger SMB-Pfad: "{smb_path}". '
            f'Erwartetes Format: \\\\server\\share\\pfad'
        )

    server = parts[0]
    share = parts[1]
    remote_path = '/'.join(parts[2:]) if len(parts) > 2 else ''

    return server, share, remote_path


def test_smb_connection(smb_path, username, password):
    """Test if an SMB connection can be established.

    Args:
        smb_path: UNC path to the SMB share.
        username: SMB username.
        password: SMB password.

    Returns:
        Tuple of (success: bool, message: str).
    """
    try:
        import smbclient
        from smbprotocol.exceptions import SMBException

        server, share, remote_path = parse_smb_path(smb_path)

        # Reset any cached session for this server
        smbclient.reset_connection_cache()
        smbclient.register_session(
            server,
            username=username,
            password=password,
            connection_timeout=10,
        )

        # Try listing the share root to verify access
        full_path = f'\\\\{server}\\{share}'
        if remote_path:
            full_path += '\\' + remote_path.replace('/', '\\')

        entries = smbclient.listdir(full_path)
        return True, f'Verbindung erfolgreich! ({len(entries)} Einträge gefunden)'

    except ImportError:
        return False, 'smbprotocol ist nicht installiert.'
    except ValueError as e:
        return False, str(e)
    except SMBException as e:
        return False, f'SMB-Fehler: {e}'
    except OSError as e:
        return False, f'Netzwerk-Fehler: {e}'
    except Exception as e:
        return False, f'Fehler ({type(e).__name__}): {e}'


def _clean_smb_dir(unc_path):
    """Recursively delete all contents of an SMB directory (but keep the directory itself).

    Args:
        unc_path: Full UNC path to the directory to clean.
    """
    import smbclient
    from smbclient import listdir, stat as smb_stat, remove as smb_remove, rmdir as smb_rmdir
    import stat

    try:
        entries = listdir(unc_path)
    except OSError:
        return  # Directory doesn't exist, nothing to clean

    for entry in entries:
        full_path = unc_path + '\\' + entry
        try:
            entry_stat = smb_stat(full_path)
            if stat.S_ISDIR(entry_stat.st_mode):
                # Recursively clean and then remove subdirectory
                _clean_smb_dir(full_path)
                smb_rmdir(full_path)
            else:
                smb_remove(full_path)
        except OSError:
            pass  # Skip entries that can't be accessed


def upload_to_smb(smb_path, username, password, local_dir):
    """Upload the contents of a local directory to an SMB share.

    The directory structure is preserved. For each subdirectory in local_dir,
    a corresponding directory is created on the SMB share.
    Old contents are removed first to avoid stale folders.

    Args:
        smb_path: UNC path to the target SMB share directory.
        username: SMB username.
        password: SMB password.
        local_dir: Path to the local directory whose contents will be uploaded.

    Raises:
        Exception: On connection or upload failures.
    """
    import smbclient

    server, share, remote_path = parse_smb_path(smb_path)

    smbclient.register_session(server, username=username, password=password)

    base_unc = f'\\\\{server}\\{share}'
    if remote_path:
        base_unc += '\\' + remote_path.replace('/', '\\')

    # Clean old contents on SMB share before uploading
    _clean_smb_dir(base_unc)

    # Ensure the base remote directory exists
    _ensure_smb_dir(base_unc)

    # Walk the local directory and upload all files
    for root, dirs, files in os.walk(local_dir):
        # Calculate relative path from local_dir
        rel_root = os.path.relpath(root, local_dir)
        if rel_root == '.':
            remote_dir = base_unc
        else:
            remote_dir = base_unc + '\\' + rel_root.replace('/', '\\')

        # Ensure remote directory exists
        _ensure_smb_dir(remote_dir)

        # Upload each file
        for filename in files:
            local_file = os.path.join(root, filename)
            remote_file = remote_dir + '\\' + filename

            with open(local_file, 'rb') as lf:
                data = lf.read()

            with smbclient.open_file(remote_file, mode='wb') as rf:
                rf.write(data)


def _ensure_smb_dir(unc_path):
    """Create an SMB directory if it does not exist.

    Args:
        unc_path: Full UNC path to the directory.
    """
    import smbclient

    try:
        smbclient.listdir(unc_path)
    except OSError:
        try:
            smbclient.mkdir(unc_path)
        except OSError:
            # Directory might have been created by another process,
            # or parent directories are missing. Try creating parents.
            _ensure_smb_dir_recursive(unc_path)


def _ensure_smb_dir_recursive(unc_path):
    """Recursively create SMB directories.

    Args:
        unc_path: Full UNC path to the directory.
    """
    import smbclient

    # Split into parent and leaf
    parts = unc_path.rsplit('\\', 1)
    if len(parts) < 2:
        return

    parent = parts[0]
    try:
        smbclient.listdir(parent)
    except OSError:
        _ensure_smb_dir_recursive(parent)

    try:
        smbclient.mkdir(unc_path)
    except OSError:
        pass  # Already exists
