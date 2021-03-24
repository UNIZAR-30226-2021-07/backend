#!/usr/bin/env bash
# Imports all submodules from a `.gitmodules` file, from
# https://stackoverflow.com/a/11258810/4266494

git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | while read -r path_key where; do
    url_key=$(echo "$path_key" | sed 's/\.path/.url/')
    url=$(git config -f .gitmodules --get "$url_key")
    rm -rf "$where"
    git submodule add "$url" "$where"
done

