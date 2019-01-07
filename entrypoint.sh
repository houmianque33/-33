wget https://github.com/almasaeed2010/AdminLTE/archive/v2.4.5.tar.gz && tar zxf v2.4.5.tar.gz && rm v2.4.5.tar.gz
mv AdminLTE-2.4.5/bower_components static/
mv AdminLTE-2.4.5/dist static/
mv AdminLTE-2.4.5/plugins static/
rm -r AdminLTE-2.4.5/
