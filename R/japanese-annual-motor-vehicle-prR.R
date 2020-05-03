## Own function to load required packages at start
load.packages <- function()
{
    library("fma", lib.loc="~/R/win-library/3.5")
    library("forecast", lib.loc="~/R/win-library/3.5")
    library("fpp", lib.loc="~/R/win-library/3.5")
    library("expsmooth", lib.loc="~/R/win-library/3.5")
    library("lmtest", lib.loc="~/R/win-library/3.5")
    library("gcookbook", lib.loc="~/R/win-library/3.5")
    library("ggplot2", lib.loc="~/R/win-library/3.5")
    library("readr", lib.loc="~/R/win-library/3.5")
    library("readxl", lib.loc="~/R/win-library/3.5")
    library("xts", lib.loc="~/R/win-library/3.5")
    library("zoo", lib.loc="~/R/win-library/3.5")
    library("tseries", lib.loc="~/R/win-library/3.5")
    library("graphics", lib.loc="C:/Program Files/R/R-3.5.1/library")
    library("methods", lib.loc="C:/Program Files/R/R-3.5.1/library")
    library("stats", lib.loc="C:/Program Files/R/R-3.5.1/library")
    library("nnet", lib.loc="C:/Program Files/R/R-3.5.1/library")
}
load.packages()





## Import excel data
library(readxl)
japanese_annual_motor_vehicle_pr <- read_excel("SIM - data and results/Tested/Annual/with horizon tests/japanese-annual-motor-vehicle-pr.xlsx")




##Convert to ts class
japanese_car_prod <- japanese_annual_motor_vehicle_pr[, 2]
japanese_car_prod.ts <- ts(japanese_car_prod, start = 1947, end = 1989, frequency = 1)
autoplot(japanese_car_prod.ts)
length(japanese_car_prod.ts)



##Partition data into test and training sets ; Test set: 1,2, 3, 6, 9, 12, 15
japanese_car_prod_test <- window(japanese_car_prod.ts, start = 1983)
japanese_car_prod_train <- window(japanese_car_prod.ts, end = 1982)

#cross check
length(japanese_car_prod_test)
length(japanese_car_prod_train)


##Forecast data for short, medium and long term horizon
models <- list(
    mod_ets = ets(japanese_car_prod_train, ic='aicc', restrict=FALSE),
    mod_arima = auto.arima(japanese_car_prod_train, stepwise=FALSE),
    mod_neural = nnetar(japanese_car_prod_train)
)



##Forecast data for short, medium and long term horizons
forecasts <- lapply(models, forecast,7 )
forecasts$snaive <- snaive(japanese_car_prod_train, 7)
par(mfrow=c(2, 2))
for(f in forecasts){
    plot(f)
    lines(japanese_car_prod_test, col='red')
}



##Check accuracy and compare models based on MASE metric
acc <- lapply(forecasts, function(f){
    accuracy(f, japanese_car_prod_test)[2,,drop=FALSE]
})
acc <- Reduce(rbind, acc)
row.names(acc) <- names(forecasts)
acc <- acc[order(acc[,'MASE']),]
round(acc, 2)