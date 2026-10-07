"""Implementations of `ArchiveClient`: the filesystem, S3 and GCS.

Membership test: the module moves bytes between a pod and one storage service and
implements the `ArchiveClient` Protocol. One module per service.
"""
