#
# libraries
#

library(RCurl)
library(XML)
library(stringi)
library(data.table)

#
# functions
#

# load spreadsheets from Google Docs
read.gdocs <- function(url) {
  cat("Reading Google Doc", url, "...\n")

  # download and parse "published" doc
  bench <- readHTMLTable(getURL(url), encoding="UTF-8", which=1, skip=1,
    colClasses=c("integer", "character", "character", "numeric", "character", "numeric", "integer", "integer"),
    header=list(c("rowid", "greek", "latin1", "score1", "latin2", "score2", "valid1", "valid2"))
  )
  # drop leftmost column (rowid)
  bench <- bench[,-1]

  # convert to format greek : latin : valid
  rbindlist(
    lapply(c(1:2), function(l) {
      col.lat <- paste("latin", l, sep="")
      col.val <- paste("valid", l, sep="")

      validated <- ! is.na(bench[,col.val])

      data.table(
        greek = as.character(stri_trans_nfkc(bench[validated, "greek"])),
        latin = as.character(stri_trans_nfkc(bench[validated, col.lat])),
        valid = as.integer(bench[validated, col.val])
      )
    })
  )
}

# load Tesserae's "syn-diagnostic" benchmark data
read.bench <- function(file) {
  cat("Reading benchmark", file, "...\n")

  # get data from the website
  bench <- read.table(file, header=T, encoding="UTF-8", sep="\t", stringsAsFactors=F, na.strings="NULL")

  # get the feature subscripts (1a, 3b, etc.) from colnames
  labels <- sub("trans_", "", grep("trans_", colnames(bench), value=T))

  rbindlist(
    lapply(labels, function(l) {
      col.lat <- paste("trans", l, sep="_")
      col.val <- paste("valid", l, sep="_")

      validated <- ! is.na(bench[,col.lat])

      data.table(
        greek = stri_trans_nfkc(bench[validated, "greek"]),
        latin = stri_trans_nfkc(bench[validated, col.lat]),
        valid = bench[validated, col.val]
      )
    })
  )
}

# create something like a dictionary using an environment
build.dict <- function(bench) {
  cat("Hashing benchmark of", nrow(bench), "row ...\n")

  dict <- new.env(hash=T, size=nrow(bench))

  do.call(Vectorize(function(greek, latin, valid) {
    key <- paste(stri_escape_unicode(greek), latin, sep="")
    assign(key, valid, envir=dict)
  }), bench)

  return(dict)
}

# load the feature set with similarity scores
read.trans <- function(file) {
  cat("Reading trans file", file, "...\n")

  trans <- fread(file, header=F)

  rbind(
    trans[,.(greek=V1, latin = sub(":.+", "", V2), score = sub(".+:", "", V2), rank=1)],
    trans[,.(greek=V1, latin = sub(":.+", "", V3), score = sub(".+:", "", V3), rank=2)],
    trans[,.(greek=V1, latin = sub(":.+", "", V4), score = sub(".+:", "", V4), rank=3)]
  )[,c("greek", "latin", "score", "rank") := list(
    stri_trans_nfkc(greek),
    stri_trans_nfkc(latin),
    as.numeric(score), as.integer(rank))]
}

# precision/recall function
test.p <- function (p.vals, trans.frame) {
  # don't count rows for which validation hasn't been done
  trans.frame <- trans.frame[! is.na(trans.frame$valid2), ]

  do.call(rbind,
    lapply(p.vals, function(v) {
      subset.frame <- subset(trans.frame, score2 > v)

      # recall = number valid / total number of greek words
      r <- sum(subset.frame$valid2) / nrow(trans.frame)
      # precision = number valid / total number of translations
      p <- sum(subset.frame$valid2) / nrow(subset.frame)
      # custom f measure
      f <- ((6^2 + 1) * r * p) / ((6^2 * r) + p)

      data.frame(v=v, r=r, p=p, f=f)
    })
  )
}

# download benchmark data if it can't be found locally

dl.bench.data <- function(gdocs = NA, tess=NA, dest="") {
  if (is.na(gdocs)) {
    gdocs = c(
      "https://docs.google.com/spreadsheets/d/19j8odaCndSXzUazCaGkHH7-AkreK59EwUn29H2cWtnM/pubhtml?gid=216846899&single=true",
      "https://docs.google.com/spreadsheets/d/1uY7jYFVVFGt4oIXktgbbRs1DNrUCPbJyqWRBs25xazA/pubhtml?gid=1218105804&single=true"
    )
  }
  if (is.na(tess)) {
    tess = "http://tess-dev.caset.buffalo.edu/cgi-bin/syn-diagnostic-dl.pl"
  }

  # compile benchmark from online sources
  bench <- rbind(
    read.gdocs(url.libby),
    read.gdocs(url.natty),
    read.bench(url.bench)
  )
  setkey(bench, greek, latin)
  bench <- unique(bench)

  # write to file
  write.table(file=file.path(dest, "dictionary-benchmark.csv"), row.names=F, quote=T, sep=",", fileEncoding = "UTF-8")
}

#
# executed code starts here
#

# load data

dest <- "data"

# download benchmark if not present
if (! file.exists(file.path(dest, "dictionary-benchmark.csv"))) {
  dl.bench.data(dest=dest)
}

# now read the benchmark
bench <- fread(file.path(dest, "dictionary-benchmark.csv"))
setkey(bench, greek, latin)

#
# testing
#

# read translation set to be checked
cat("Select translation file to check...\n")
file.trans <- file.choose()

# load featureset with similarity scores
trans <- read.trans(file.trans)
setkey(trans, greek, rank)

trans <- trans[intersect(bench$greek, trans$greek),]
setkey(trans, rank, score)

# test primary cutoff

res <- do.call(rbind,
  lapply(seq(from = .1, to = .9, by = .01), function(cutoff) {
    valid <- bench[trans[rank == 1 & score >= cutoff, .(greek, latin)], valid]
    right <- sum(valid, na.rm=T)
    missing <- sum(is.na(valid))
    wrong <- length(valid) - right - missing
    data.frame(cutoff=cutoff, right=right, wrong=wrong, missing=missing)
  })
)

pdf(file="~/Desktop/t1.precision.pdf", width=8, height=6, pointsize=14)
with(res, plot(cutoff, right/(right+wrong), ylab="% correct", xlab="similarity threshold", xaxt="n", yaxt="n"))
mtext(text = c("low", "high"), side=2, line=1, adj=c(0,1), at=with(res, c(min(right/(right+wrong)), max(right/(right+wrong)))))
mtext(text = c("low", "high"), side=1, line=1, adj=c(0,1), at=c(0.1,0.9))
dev.off()

pdf(file="~/Desktop/t1.recall.pdf", width=8, height=6, pointsize=14)
with(res, plot(cutoff, right/375, ylab="# translations", xlab="similarity threshold", xaxt="n", yaxt="n"))
mtext(text = c("low", "high"), side=2, line=1, adj=c(0,1), at=with(res, c(min(right/375), max(right/375))))
mtext(text = c("low", "high"), side=1, line=1, adj=c(0,1), at=c(0.1,0.9))
dev.off()

