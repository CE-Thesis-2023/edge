from hanging_threads import start_monitoring

from edge.run import Application

# start_monitoring(seconds_frozen=10, test_interval=100)

if __name__ == "__main__":
    app = Application()
    app.run()
