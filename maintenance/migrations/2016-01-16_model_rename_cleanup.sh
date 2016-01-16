#! /bin/bash

echo '.quit' \
  | sqlite3 photos.db --echo -init maintenance/migrations/2016-01-16_model_rename_cleanup_1.sql \
  && ./setup.py \
  && echo '.quit' \
  | sqlite3 photos.db --echo -init maintenance/migrations/2016-01-16_model_rename_cleanup_2.sql
