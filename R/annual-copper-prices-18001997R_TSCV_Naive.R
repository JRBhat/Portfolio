#library(readxl)
#annual_copper_prices_18001997OK <- read_excel("F:/MASTER THESIS/R files/SIM - data and results/Tested/Annual/with horizon tests/annual-copper-prices-18001997OK.xlsx")


##Convert to ts class
dataset <-  annual_copper_prices_18001997OK[, 2]#choose second column from original dataset
str(dataset)
dataset.ts <- ts(dataset, start = 1800, end = 1997, frequency = 1)#yearly
autoplot(dataset.ts)
length(dataset.ts)
length(dataset.ts)


##Partition data into test and training sets 
test_set <- window(dataset.ts, start = 1990)
train_set <- window(dataset.ts, end = 1989)

##check
length(test_set)
length(train_set)

# STL Decomposition 
autoplot(mstl(dataset.ts))

##Fitting the model

models <- list(
    mod_ets = ets(train_set, ic = 'aicc', restrict = FALSE),
    mod_arima = auto.arima(train_set, ic = 'aicc', stepwise = TRUE),
    mod_neural = nnetar(train_set)
)

##Generate forecasts 
forecasts <- lapply(models, forecast, 8, PI = TRUE)
forecasts$snaive <- snaive(train_set, 8)#attach the snaive forecast to the models list and plot them together
par(mfrow = c(2, 2))
for (f in forecasts) {
    plot(f)
    lines(test_set, col = 'red')
}

##Check accuracy and compare models based on MASE metric
acc <- lapply(forecasts, function(f){
    accuracy(f, test_set)[2,,drop = FALSE]#drops the training set
})

acc
#str(acc)# list containing the summary stats of the training and test sets


acc <- Reduce(rbind, acc)#Reduce function applies the rbind function to all the elements of the acc object itertively.
acc
class(acc)
str(acc)
row.names(acc) <- names(forecasts)#gives names for each row
acc
acc <- acc[order(acc[,'MASE']),]#arrange according to the MASE

#?order
round(acc, 2)

# Set up forecast functions for ETS and ARIMA models
fets <- function(x, h) {
    forecast(ets(x), h = h)
}
farima <- function(x, h) {
    forecast(auto.arima(x), h = h)
}
fneural <- function(x, h){
    forecast(nnetar(x), h = h)
}
fnaive <- function(x, h){
    forecast(naive(x), h = h)
}

x = 1

# Compute CV errors for ETS as e1
e1 <- tsCV(dataset.ts, fets, x)

# Compute CV errors for ARIMA as e2
e2 <- tsCV(dataset.ts, farima, x)

# Compute CV errors for NEURAL as e3
e3 <- tsCV(dataset.ts, fneural, x)

# Compute CV errors for SNAIVE as e4
e4 <- tsCV(dataset.ts, fnaive, x)

#View the Errors matrix
errors <- list(ETS = e1, ARIMA =  e2, NEURAL =  e3, NAIVE = e4)
errors
plotted_errors <- lapply(errors, plot)


# Find MSE of each model class
mse1 <- mean(e1^2, na.rm = TRUE)
mse1
mse2 <- mean(e2^2, na.rm = TRUE)
mse2
mse3 <- mean(e3^2, na.rm = TRUE)
mse3
mse4 <- mean(e4^2, na.rm = TRUE)
mse4

mse_vec <- c(mse1, mse2, mse3, mse4)
names(mse_vec) <- c('ETS', 'ARIMA', 'NEURAL', 'NAIVE')
MSE <- sort(mse_vec)
cbind(MSE)

Best_MSE <- names(MSE[1])
print(paste('The best forecasting model is', Best_MSE))



