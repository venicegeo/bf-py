# beachfront-py
# https://github.com/venicegeo/beachfront-py

# Copyright 2016, RadiantBlue Technologies, Inc.

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

FROM venicegeo/beachfront:latest

WORKDIR $BUILD

COPY requirements*txt $BUILD/

RUN \
    pip install -r requirements.txt; \
    pip install -r requirements-dev.txt

COPY . $BUILD/

RUN pip install .

WORKDIR /home/geolambda
