#!/bin/bash

rm -rf node_modules
npm ci --include=optional
npm run build
