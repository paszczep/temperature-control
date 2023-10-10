FROM public.ecr.aws/lambda/python@sha256:489d4abc8644060e2e16db2ffaaafa157359761feaf9438bf26ed88e37e43d9c as build
RUN yum install -y unzip && \
    curl -Lo "/tmp/chromedriver.zip" "https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip" && \
    curl -Lo "/tmp/chrome-linux.zip" "https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F1135561%2Fchrome-linux.zip?alt=media" && \
    unzip /tmp/chromedriver.zip -d /opt/ && \
    unzip /tmp/chrome-linux.zip -d /opt/
#
FROM public.ecr.aws/lambda/python@sha256:489d4abc8644060e2e16db2ffaaafa157359761feaf9438bf26ed88e37e43d9c
RUN yum install atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel -y
COPY --from=build /opt/chrome-linux /opt/chrome
COPY --from=build /opt/chromedriver /opt/
ENV TZ=Europe/Berlin
COPY src ./src
COPY .env ./
COPY requirements.txt ./
RUN pip install -r requirements.txt
RUN rm requirements.txt
WORKDIR /var/task
CMD ["src.run.handler"]
