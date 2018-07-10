import hashlib
import os

def generate_sha_hash_helper(case_path):
    sha_hasher = hashlib.sha256()
    with open(case_path, 'rb') as case_file:
        sha_hasher.update(case_file.read())

    return sha_hasher.hexdigest()

def read_sha_from_file_helper(file_path):
    with open(file_path) as sha_file:
        sha = sha_file.read()

    return sha

def write_sha_to_file_helper(sha, file_path):
    with open(file_path, 'w') as sha_file:
        sha_file.write(sha)

# this file provides a way to automatically generate
# sha 256 hashes for the files inside CASE_DIR. It
# must be ran from the project root as it uses the
# current working directory to figure out paths
if __name__ == '__main__':
    SHA_DIR = os.path.join(os.getcwd(), 'tests/sha')
    CASE_DIR = '/Users/junxuan/Downloads/test'

    for case_path in os.listdir(CASE_DIR):
        filename, _ = os.path.splitext(case_path)
        case_sha = generate_sha_hash_helper(os.path.join(CASE_DIR, case_path))
        write_sha_to_file_helper(case_sha, os.path.join(SHA_DIR, filename + '.sha'))
