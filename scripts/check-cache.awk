/^#[0-9]+ \[dependencies .*RUN npm ci/ { deps = $1 }
/^#[0-9]+ \[browser .*RUN npx playwright install/ { browser = $1 }
$1 == deps && $2 == "CACHED" { deps_cached = 1 }
$1 == browser && $2 == "CACHED" { browser_cached = 1 }
END {
    if (!deps_cached || !browser_cached) {
        print "Cache check failed: npm and Chromium installation must both be CACHED"
        exit 1
    }
    print "Cache verified: npm dependencies and Chromium installation are CACHED"
}
