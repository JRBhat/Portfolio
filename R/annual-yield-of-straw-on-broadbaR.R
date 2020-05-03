## Own function to load required packages at start
load.packages <- function()
{
    library("fma", lib.loc="~/R/win-library/3.4")
    library("fpp", lib.loc="~/R/win-library/3.4")
    library("gcookbook", lib.loc="~/R/win-library/3.4")
    library("ggplot2", lib.loc="~/R/win-library/3.4")
    library("readr", lib.loc="~/R/win-library/3.4")
    library("readxl", lib.loc="~/R/win-library/3.4")
    library("xts", lib.loc="~/R/win-library/3.4")
    library("graphics", lib.loc="C:/Program Files/R/R-3.4.4/library")
    library("methods", lib.loc="C:/Program Files/R/R-3.4.4/library")
    library("stats", lib.loc="C:/Program Files/R/R-3.4.4/library")
    library("nnet", lib.loc="C:/Program Files/R/R-3.4.4/library")
}
load.packages()




## Import excel data
library(readxl)
annual_yield_of_straw_on_broadba <- read_excel("SIM - data and results/Tested/Annual/with horizon tests/annual-yield-of-straw-on-broadba.xlsx")
straw <- annual_yield_of_straw_on_broadba[ ,2]





##Convert to ts class
straw.ts <- ts(straw, start = 1852, end = 1925, frequency = 1)
autoplot(straw.ts)
length(straw.ts)



##Partition data into test and training sets ; Test set: 5, 10, 15
straw_test <- window(straw.ts, start = 1916)
straw_train <- window(straw.ts, end = 1915)

#check
length(straw_test)
length(straw_train)




##Forecast data for short, medium and long term horizon
models <- list(
    mod_ets = ets(straw_train, ic='aicc', restrict=FALSE),
    mod_arima = auto.arima(straw_train, stepwise=FALSE),
    mod_neural = nnetar(straw_train)
)




##Forecast data for short, medium and long term horizons
forecasts <- lapply(models, forecast, 10)
forecasts$snaive <- snaive(straw_train, 10)
par(mfrow=c(2, 2))
for(f in forecasts){
    plot(f)
    lines(straw_test, col='red')
}




##Check accuracy and compare models based on MASE metric
acc <- lapply(forecasts, function(f){
    accuracy(f, straw_test)[2,,drop=FALSE]
})
acc <- Reduce(rbind, acc)
row.names(acc) <- names(forecasts)
acc <- acc[order(acc[,'MASE']),]
round(acc, 2)

