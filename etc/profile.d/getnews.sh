#!/bin/sh
gethostnews() {
  if [ -x /usr/bin/curl ]; then
    /usr/bin/curl -s --connect-timeout 2 "$1" && touch /tmp/gotnews
    return
  fi

  if [ -x /usr/bin/wget ]; then
    /usr/bin/wget -qO- --connect-timeout 2 "$1" && touch /tmp/gotnews
    return
  fi
}

case $- in
  *i*) [ ! -f /tmp/gotnews ] && gethostnews "https://news.contabo.com/host/$(hostname -s)" ;;
  *) return ;;
esac

unset -f gethostnews
