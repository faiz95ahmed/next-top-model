
var elemMap = new Map() // stores chart context, dataset, progress_bar, original_data, and log box

var socket = new WebSocket('ws://localhost:8000/ws/graph/');

socket.onmessage = function(e){
    var eventData = JSON.parse(e.data);
    var job_name = eventData.job_name;
    var job_data = elemMap.get(job_name);
    var djangoData = JSON.parse(eventData.text);
    if (djangoData.abort_ack) {
        job_data.abortButton.setAttribute("class", "abortbutton btn btn-success");
        job_data.abortButton.innerHTML = "  Abort Acknowledged!";
    }
    var dataset = job_data.graphData.data.datasets;
    var trainData = dataset[0].data;
    var validationData = dataset[1].data;
    var newGraphLabels = job_data.graphData.data.labels;
    var max_epoch = djangoData.epoch;
    if ((max_epoch != null) & (newGraphLabels.length - 1 < max_epoch)) {   
        job_data.myChart.data.labels = [...Array(max_epoch + 1).keys()];
    }
    combined_data = add_data(max_epoch, trainData, validationData, djangoData.progress);
    job_data.myChart.data.datasets[0].data = combined_data[0];
    job_data.myChart.data.datasets[1].data = combined_data[1];
    job_data.myChart.update();
    updateLogbox(job_data.logbox, djangoData.logs, job_name);
    updateProgress(job_data.bar,
                   {percent: djangoData.progress[max_epoch].train_progress * 100, current: djangoData.progress[max_epoch].train_progress * 100, total: 100},
                   max_epoch);
    // validation_progress = djangoData.progress[max_epoch].validation_progress;
    
}

function logObjectToP(logObject, job_name) {
    const logLevel = logObject.level;
    var timeElem = document.createElement('timestamps-'+job_name);
    timeElem.innerText = logObject.time + " ";
    var orderElem = document.createElement('orderstamps-'+job_name);
    orderElem.innerText = logObject.order.padStart(10, " ") + " ";
    var message = logObject.message;
    var p = document.createElement("p");
    p.style="margin-bottom:0";
    if (logLevel == "WARNING") {
        p.style.color = "yellow";
    } else if (logLevel == "ERROR") {
        p.style.color = "red";
    } else if (logLevel == "DEBUG") {
        p.style.color = "lightblue";
    } else if (logLevel == "CRITICAL") {
        p.style.color = "red";
        message = message.bold();
    } else {
        p.style.color = "white";
    };
    var messageElem = document.createElement(null);
    messageElem.innerText = message;
    p.appendChild(orderElem);
    p.appendChild(timeElem);
    p.appendChild(messageElem);
    return p;
}

function updateLogbox(logbox, newLogs, job_name) {
    var logboxElement = logbox.logboxElement;
    var logboxSheet = logbox.logboxSheet;
    logboxSheet.innerHTML = "";
    if (!logbox.logboxOrderCheckbox.checked) {
        logboxSheet.innerHTML += "orderstamps-" + job_name + " {visibility: hidden; font-size: 0;}"
    };
    if (!logbox.logboxTimeCheckbox.checked) {
        logboxSheet.innerHTML += "timestamps-" + job_name + " {visibility: hidden; font-size: 0;}"
    };
    for (const logObject of newLogs) {
        logboxElement.appendChild(logObjectToP(logObject, job_name));
        logboxElement.scrollTop = logboxElement.scrollHeight;
    }
}

function updateProgress(progressBarElement, progress, epoch) {
    progressBarElement.style.width = progress.percent + "%";
    progressBarElement.setAttribute("aria-valuenow", '"' + progress.percent + '"');
    progressBarElement.innerHTML = "Epoch " + epoch + ": "+ progress.current + "%";
}

function new_canvas_data(job_name, orig_data) {
    var ctx = document.getElementById('myChart-'.concat(job_name)).getContext('2d');
    var train_losses = [];
    var validation_losses = [];
    if (orig_data.length > 0) {
        var max_epoch = orig_data[orig_data.length -1].epoch;
        add_data(max_epoch, train_losses, validation_losses, orig_data);
        var labels = [...Array(max_epoch + 1).keys()]
    } else {
        var labels = []
    }

    var dataset = [{
        label: 'Train Loss',
        data: train_losses,
        borderColor: 'rgb(255, 99, 132)',
        cubicInterpolationMode: 'monotone',
        tension: 0.4
    },
    {
        label: 'Validation Loss',
        data: validation_losses,
        borderColor: 'rgb(54, 162, 235)',
        cubicInterpolationMode: 'monotone',
        tension: 0.4
    }];
    var graphData = {
        type: 'line',
        data: {
            labels: labels,
            datasets: dataset
        },
        options: {}
    };
    var myChart = new Chart(ctx, graphData);
    var bar = document.getElementById("progress-bar-".concat(job_name));
    var sheet = document.createElement('style')
    
    document.body.appendChild(sheet);
    var logbox = {
        logboxElement: document.getElementById("log-box-".concat(job_name)),
        logboxTimeCheckbox: document.getElementById("showLogTime-".concat(job_name)),
        logboxOrderCheckbox: document.getElementById("showLogOrder-".concat(job_name)),
        logboxSheet: sheet
    };
    var abortButton = document.getElementById("abort-".concat(job_name))
    elemMap.set(job_name, {'context': ctx, 'orig_data': orig_data, 'graphData': graphData, 'myChart': myChart, 'bar': bar, 'logbox': logbox, 'abortButton': abortButton});
}

function interpolate(arr, initial_val) {
    if (arr[0] == null) {arr[0] = initial_val;}
    var last_valid = 0;
    for (var i = 1; i < arr.length; i++) {
        if (arr[i] != null) {
            if (i > (last_valid + 1)) {
                // interpolate
                const delta = (arr[i] - arr[last_valid]) / (i - last_valid)
                for (var j = last_valid + 1; j < i; j ++) {
                    arr[j] = arr[j - 1] + delta;
                }
            }
            last_valid = i;
        }
    }
    return arr;
}

function add_data(max_epoch, train_losses, validation_losses, new_data) {
    // expand size of datasets
    for (var i = train_losses.length; i <= max_epoch; i++) {
        train_losses.push(null);
        validation_losses.push(null);
    }
    // add new data
    for (const k of Object.keys(new_data)) {
        const jsonline = new_data[k];
        const epoch = parseInt(jsonline.epoch);
        train_losses[epoch] = jsonline.train_loss;
        validation_losses[epoch] = jsonline.validation_loss;
    }
    // interpolate missing values - would be better to remove x labels of missing values and allow chart.js to do the interpolation
    train_losses = interpolate(train_losses, 0);
    validation_losses = interpolate(validation_losses, 0);
    return [train_losses, validation_losses];
}

window.addEventListener("load", function(){
    var job_names = JSON.parse(document.getElementById('job-names').innerText);

    var dumped_vals = JSON.parse(document.getElementById('dumped-vals').innerText);

    for (const job_name of job_names) {
        new_canvas_data(job_name, JSON.parse(dumped_vals[job_name]));
    }
});