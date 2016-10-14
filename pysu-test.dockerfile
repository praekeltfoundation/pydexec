# This code is a modified version of that found in the gosu project by Tianon
# Gravi: https://github.com/tianon/gosu/blob/1.10/Dockerfile.test
# That project is licensed under the GPL-3.0 license. The text for that license
# can be found in the 'GPL.txt' file.

FROM pydexec:test-base

# add "nobody" to ALL groups (makes testing edge cases more interesting)
RUN cut -d: -f1 /etc/group | xargs -n1 addgroup nobody

RUN { \
		echo '#!/bin/sh'; \
		echo 'set -ex'; \
		echo; \
		echo 'spec="$1"; shift'; \
		echo; \
		echo 'expec="$1"; shift'; \
		echo 'real="$(pysu "$spec" id -u):$(pysu "$spec" id -g):$(pysu "$spec" id -G)"'; \
		echo '[ "$expec" = "$real" ]'; \
		echo; \
		echo 'expec="$1"; shift'; \
		# have to "|| true" this one because of "id: unknown ID 1000" (rightfully) having a nonzero exit code
		echo 'real="$(pysu "$spec" id -un):$(pysu "$spec" id -gn):$(pysu "$spec" id -Gn)" || true'; \
		echo '[ "$expec" = "$real" ]'; \
	} > /usr/local/bin/pysu-t \
	&& chmod +x /usr/local/bin/pysu-t

# adjust users so we can make sure the tests are interesting
RUN set -x \
	&& python="$(readlink -f "$(which python)")" \
	&& chgrp nogroup "$python" \
	&& chmod +s "$python"
USER nobody
ENV HOME /omg/really/pysu/nowhere
# now we should be nobody, ALL groups, and have a bogus useless HOME value

RUN id

#RUN pysu-t 0 "0:0:$(id -G root)" "root:root:$(id -Gn root)"
RUN pysu-t 0:0 '0:0:0' 'root:root:root'
RUN pysu-t root "0:0:$(id -G root)" "root:root:$(id -Gn root)"
RUN pysu-t 0:root '0:0:0' 'root:root:root'
RUN pysu-t root:0 '0:0:0' 'root:root:root'
RUN pysu-t root:root '0:0:0' 'root:root:root'
RUN pysu-t 1000 "1000:$(id -g):$(id -g)" "1000:$(id -gn):$(id -gn)"
RUN pysu-t 0:1000 '0:1000:1000' 'root:1000:1000'
RUN pysu-t 1000:1000 '1000:1000:1000' '1000:1000:1000'
RUN pysu-t root:1000 '0:1000:1000' 'root:1000:1000'
RUN pysu-t 1000:root '1000:0:0' '1000:root:root'
RUN pysu-t 1000:daemon "1000:$(id -g daemon):$(id -g daemon)" '1000:daemon:daemon'
RUN pysu-t games "$(id -u games):$(id -g games):$(id -G games)" 'games:games:games'
RUN pysu-t games:daemon "$(id -u games):$(id -g daemon):$(id -g daemon)" 'games:daemon:daemon'

RUN pysu-t 0: "0:0:$(id -G root)" "root:root:$(id -Gn root)"
# FIXME: Under Alpine this call will fail as there are too many groups and
# musl's `setgroups()` will fail :-(
RUN pysu-t '' "$(id -u):$(id -g):$(id -G)" "$(id -un):$(id -gn):$(id -Gn)"
RUN pysu-t ':0' "$(id -u):0:0" "$(id -un):root:root"

RUN [ "$(pysu 0 env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu 0:0 env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu root env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu 0:root env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu root:0 env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu root:root env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu 0:1000 env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu root:1000 env | grep '^HOME=')" = 'HOME=/root' ]
RUN [ "$(pysu 1000 env | grep '^HOME=')" = 'HOME=/' ]
RUN [ "$(pysu 1000:0 env | grep '^HOME=')" = 'HOME=/' ]
RUN [ "$(pysu 1000:root env | grep '^HOME=')" = 'HOME=/' ]
RUN [ "$(pysu games env | grep '^HOME=')" = 'HOME=/usr/games' ]
RUN [ "$(pysu games:daemon env | grep '^HOME=')" = 'HOME=/usr/games' ]

# something missing?  some other functionality we could test easily?  PR! :D
