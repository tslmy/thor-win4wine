#!/usr/bin/env python3
"""Replay a linear history as sanitized snapshots using GitButler, never force-push.

Run only after auditing the input. The output must not already exist. Redactions
are a private JSON object mapping exact sensitive strings to public replacements.
That map and the original repository are never copied into the output history.
"""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile


def command(*args, cwd=None, env=None):
    return subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True,
                          stdout=subprocess.PIPE, text=True).stdout.strip()


def scrub(data, replacements):
    text = data.decode('utf-8')
    for old, new in replacements.items():
        if not old:
            raise ValueError('Redaction keys may not be empty.')
        text = text.replace(old, new)
    return text.encode('utf-8')


def replay(source, destination, replacements):
    if destination.exists():
        raise SystemExit('Refusing existing output. Original and earlier publication copies are never overwritten.')
    commits = command('git', 'rev-list', '--reverse', 'HEAD', cwd=source).splitlines()
    for revision in commits:
        parents = command('git', 'rev-list', '--parents', '-n', '1', revision, cwd=source).split()
        if len(parents) > 2:
            raise SystemExit('This helper preserves linear histories only; a merge needs a reviewed migration plan.')
    destination.mkdir(parents=True)
    command('but', 'init', cwd=destination)
    command('but', 'config', 'user', 'set', 'name', 'Thor contributors', cwd=destination)
    command('but', 'config', 'user', 'set', 'email', 'contributors@example.invalid', cwd=destination)
    previous = set()
    mapping = {}
    for index, revision in enumerate(commits):
        blob = subprocess.check_output(['git', 'archive', '--format=tar', revision], cwd=source)
        current = set()
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            for entry in archive.getmembers():
                if entry.isdir():
                    continue
                if not entry.isfile() or Path(entry.name).is_absolute() or '..' in Path(entry.name).parts:
                    raise SystemExit('Only safe regular text files may enter the public history.')
                data = archive.extractfile(entry).read()
                if b'\0' in data or data.startswith((b'MZ', b'\x7fELF', b'PK\x03\x04')):
                    raise SystemExit(f'Binary encountered in {entry.name}; audit it before publishing.')
                data = scrub(data, replacements)
                path = destination / entry.name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                path.chmod(0o755 if entry.mode & 0o111 else 0o644)
                current.add(entry.name)
        for name in previous - current:
            (destination / name).unlink()  # only files this replay created
        message = command('git', 'show', '-s', '--format=%B', revision, cwd=source)
        message = scrub(message.encode(), replacements).decode()
        timestamp = command('git', 'show', '-s', '--format=%aI', revision, cwd=source)
        env = dict(os.environ, GIT_AUTHOR_NAME='Thor contributors', GIT_AUTHOR_EMAIL='contributors@example.invalid',
                   GIT_COMMITTER_NAME='Thor contributors', GIT_COMMITTER_EMAIL='contributors@example.invalid',
                   GIT_AUTHOR_DATE=timestamp, GIT_COMMITTER_DATE=timestamp)
        # There is no unrelated work in this newly created repository.
        command('but', 'commit', '-m', message, cwd=destination, env=env)
        if index == 0:
            branch = command('git', 'symbolic-ref', '--short', 'HEAD', cwd=destination)
            if branch != 'main':
                command('but', 'reword', branch, '-m', 'main', cwd=destination)
        authors = command('git', 'show', '-s', '--format=%an <%ae>%n%cn <%ce>', 'HEAD', cwd=destination)
        if authors.splitlines() != ['Thor contributors <contributors@example.invalid>'] * 2:
            raise SystemExit('Commit metadata was not anonymized; do not publish.')
        mapping[revision] = command('git', 'rev-parse', 'HEAD', cwd=destination)
        previous = current
    branch = command('git', 'symbolic-ref', '--short', 'HEAD', cwd=destination)
    if branch != 'main':
        # GitButler may place work ahead of its local main target in a topic
        # bucket. Land that bucket locally before any remote is configured.
        command('but', 'merge', branch, '--yes', '--ff-only', cwd=destination)
    if command('git', 'rev-parse', 'main', cwd=destination) != command('git', 'rev-parse', 'HEAD', cwd=destination):
        raise SystemExit('main does not name the complete sanitized history; do not publish.')
    if int(command('git', 'rev-list', '--count', 'main', cwd=destination)) != len(commits):
        raise SystemExit('Sanitized history length differs; do not publish.')
    # Keep private original-to-public mapping OUTSIDE the new repository.
    destination.with_suffix('.commit-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
    print(f'Replayed {len(commits)} sanitized commits on main in {destination}. Nothing pushed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--redactions', type=Path, required=True)
    args = parser.parse_args()
    replay(args.source.resolve(), args.destination.resolve(), json.loads(args.redactions.read_text()))
