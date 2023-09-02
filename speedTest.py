from time import sleep
import speedtest
import datetime
import csv
import pandas as pd


def get_results():
    st = speedtest.Speedtest()
    l = [str(datetime.datetime.today()), str(st.download()/(1024*1024)), str(st.upload()/(1024*1024)), str(st.results.ping)]
    return l


def read_csv(filename=None):

    df = pd.read_csv(filename)
    print(df)


if __name__ == '__main__':
    while True:
        with open('sheet.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(get_results())

        file.close()

        sleep(60)

