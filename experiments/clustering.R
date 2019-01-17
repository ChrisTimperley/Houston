library("dtwclust")
library("optparse")

option_list = list(
  make_option("--data_dir", type="character", default=NULL, 
              help="path to the data directory."),
  make_option(c("-c", "--command"), type="character", default=NULL, 
              help="desired command."),
  make_option("--output_dir", type="character", default="", 
              help="path to the output directory."),
  make_option(c("-n", "--dp_num"), type="integer", default=-1,
              help="number of datapoints per trace."),
  make_option(c("-k", "--clusters"), type="integer", default=3, 
              help="number of clusters (k)."),
  make_option("--fuzzy", action="store_true", default=FALSE, 
              help="run the clustering in fuzzy mode.")
); 

opt_parser = OptionParser(option_list=option_list);
opt = parse_args(opt_parser);

if(is.null(opt$data_dir) || is.null(opt$command)) {
  print_help(opt_parser)
  stop("Required arguments missing!")
}

allfiles <- list.files(path=opt$data_dir, pattern=paste("factory.", opt$command, ".+.csv", sep=""), full.names=TRUE, recursive=FALSE)

myData <- list()
files <- vector()
i <- 1
n <- opt$dp_num
for (f in allfiles) {
  m <- read.csv(f, header=TRUE)
  m <- as.matrix(m)
  if (n != -1) {
    l <- floor(length(m[, 1]) / n)
    if (l == 0) {
        next
    }
    m <- m[seq(0, n-1) * l + 1 , ]
  }
  myData[[i]] <- m
  files[i] <- f
  i <- i+1
}

write(files, file=paste(opt$output_dir, opt$command, "_files.txt", sep=""))

#myData2 <- zscore(myData)
#m <- read.csv(files[1], header=TRUE)

if (!opt$fuzzy) {
    mvc <- tsclust(myData, k = opt$clusters, distance = "dtw", seed = 390L)
} else {
    mvc <- tsclust(myData, k = opt$clusters, type = "fuzzy", seed = 390L)
}
pdf(paste(opt$output_dir, opt$command, ".pdf", sep=""))
plot(mvc)
dev.off()
write(paste("Int64", toString(mvc@cluster), sep = "\n"), file=paste(opt$output_dir, opt$command, "_labels.txt", sep=""))
save.image(file=paste(opt$output_dir, opt$command, ".RData", sep=""))


