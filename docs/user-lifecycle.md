# User administration: SSH keys and removal

## SSH
In the Users tab, an authorized administrator can generate an Ed25519
keypair for a regular Linux account (UID >= 1000, home /home/NAME).
The server invokes ssh-keygen with a fixed argument list, appends the public
key to the target user's ~/.ssh/authorized_keys and returns the private key
exactly once over the authenticated panel connection. No private key is
intentionally retained on disk after the request; temporary files are
deleted, but backups, browser memory or server diagnostics may still be
relevant. Avoid exposing this endpoint directly on the internet.

Download the private key with file permissions 0600. Login example:
```bash
chmod 600 id_ed25519
ssh -i ./id_ed25519 USER@SERVER
```
The SSH daemon must permit public-key authentication. This feature does
not turn on password-based SSH authentication.

## Deleting a user
The panel offers a read-only preview followed by exact typed
confirmation `DELETE username` and a second confirmation.
Root, ubuntu, the logged-in administrator, and system accounts cannot
be deleted. A user with an active login or running processes is refused.
The implementation removes the Linux account and conventional home,
including local rootless Podman storage under that home, using
`userdel --remove` after disabling linger.

**Incomplete cleanup:** host-level storage outside /home/NAME, named
volumes held elsewhere, routes stored in the Traefik manifest, backup
archives and network allocations require separate review. This endpoint
does not claim to remove all containers/images in external storage.
The user should stop and inspect user services before deleting.

## Security limitation
The current dashboard daemon still runs privileged. The lifecycle routes
must be migrated into an isolated, audited operations service with
strict authorization and test coverage before any production exposure.
Install only on a disposable environment until that is done.
