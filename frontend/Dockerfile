FROM nginx:alpine

# Copy static frontend files to Nginx default serving directory
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
