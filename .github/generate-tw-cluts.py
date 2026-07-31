#!/usr/bin/env python3

import sys
import argparse
import urllib.request
import subprocess

from dataclasses import dataclass


TW_GAME_PATCH_LIST_URL = "http://patch-gamever.ffxiv.com.tw/http/win32/ffxivtc_release_tc_game/2012.01.01.0000.0000/"


@dataclass
class PatchListEntry:
	size: int
	unk_game_install_size: int
	unk_int0: int
	unk_int1: int
	version: str
	patch_url: str

	@classmethod
	def from_line_str(cls, line: str):
		parts = line.split("\t")
		return PatchListEntry(int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]), parts[4], parts[5])

	def repository_slug(self) -> str:
		filename_slash_idx = self.patch_url.rfind("/")
		slug_slash_idx = self.patch_url.rfind("/", 0, filename_slash_idx)

		return self.patch_url[(slug_slash_idx + 1):filename_slash_idx:]

	def base_path_url(self) -> str:
		filename_slash_idx = self.patch_url.rfind("/")

		return self.patch_url[:filename_slash_idx]

	def __repr__(self) -> str:
		return self.version


def fetch_patch_list() -> list[PatchListEntry]:
	with urllib.request.urlopen(TW_GAME_PATCH_LIST_URL) as response:
		text: str = response.read().decode()
		body_start_idx: int = text.find("\r\n\r\n") + 4
		patch_list_end_idx: int = text.rfind("--", body_start_idx, text.rfind("--"))

		patch_lines: list[str] = text[body_start_idx:patch_list_end_idx].splitlines()
		patches: list[PatchListEntry] = list()

		for patch_line in patch_lines:
			patches.append(PatchListEntry.from_line_str(patch_line))

		return patches

def partition_patches_by_repository(patch_list: list[PatchListEntry]) -> dict[str, list[PatchListEntry]]:
	patches: dict[str, list[PatchListEntry]] = dict()
	for patch in patch_list:
		repository_slug = patch.repository_slug()

		repository_patches = patches.get(repository_slug)
		if repository_patches:
			repository_patches.append(patch)
		else:
			patches[repository_slug] = [patch]

	return patches

def generate_luts(slug: str, patches: dict[str, list[PatchListEntry]], force: bool, xiv_dl_bin):
	patch_list = patches[slug]

	proc = subprocess.Popen([xiv_dl_bin, "--verbose", "lut", "--slug", slug, "--urls"] + [patch.patch_url for patch in patch_list] + ["--output-path", f"luts/{slug}", "--compression", "Brotli"] + (["--force"] if force else []))
	proc.communicate()

def generate_cluts(slug: str, patches: dict[str, list[PatchListEntry]], force: bool, xiv_dl_bin):
	patch_list = patches[slug]
	base_patch_url = patch_list[0].base_path_url()

	proc = subprocess.Popen([xiv_dl_bin, "--verbose", "clut", "--slug", slug, "--urls"] + [patch.patch_url for patch in patch_list] + ["--base-path", f"luts/{slug}", "--base-patch-url", base_patch_url, "--output-path", f"cluts/{slug}"] + (["--force"] if force else []))
	proc.communicate()


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	
	subparsers = parser.add_subparsers(dest="subcommand", required=True)
	for subparser in [subparsers.add_parser("lut"), subparsers.add_parser("clut")]:
		subparser.add_argument("-f", "--force", action='store_true')
		subparser.add_argument("-s", "--slug", required=True)
		subparser.add_argument("-b", "--bin", default="./xiv-dl")
	
	args = parser.parse_args()


	patch_list = fetch_patch_list()

	patches = partition_patches_by_repository(patch_list)


	if args.subcommand == "lut":
		generate_luts(args.slug, patches, args.force, args.bin)
	else:
		generate_cluts(args.slug, patches, args.force, args.bin)
