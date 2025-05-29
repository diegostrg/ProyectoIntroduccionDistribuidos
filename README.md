PROYECTO SISTEMAS DISTRIBUIDOS ASIGNACION DE SALONES

hecho por:
Javier Felipe Aldana Jaramillo
Juan Diego Muñoz Angulo
David Roa Neisa

- Link video: https://drive.google.com/file/d/1NBQtpSjF_dJvCQev7iTPAYt0ecwQ8AqJ/view?usp=sharing

- Documento: https://livejaverianaedu-my.sharepoint.com/:w:/g/personal/al_javier_javeriana_edu_co/EXcIsUjxUXlOgbEjV4BzEWMBhmGJL0q0xGUo70W2kuig2w?rtime=hw8CqIad3Ug

- Informe rendimiento: https://livejaverianaedu-my.sharepoint.com/:w:/g/personal/al_javier_javeriana_edu_co/EbjmPoeG3F5Ck8_rCO7X_hcBJDz6zZ0OP70T1eeCthhGbw?e=PcGjjj

- Para probar el programa, se debe ejecutar los siguientes archivos en el siguiente orden de ejecucion (en diferentes terminales):
    - python DTI.py
    - python DTIBackup.py
    - python broker.py
    - python healthcheck.py
    - python facultad.py
    - python programa.py

- Si desea probar el funcionamiento del programa de una manera mas sencilla, ejecute el archivo Pruebador.py en otra terminal de la siguiente forma:
    - python Pruebador.py
  Despues se le desplegara un menu con las pruebas mas importantes que pueda hacer y seleccione la que desee ejecutar.

- Si desea probarlo manualmente, al ya haber ejecutado los archivos como se dice anteriormente, debe completar los parametros que pide el archivo de facultad y de programa
  para probarlo (acabe los procesos usando ctrl+c para evitar conflictos com procesos zombies).

- En caso de salir del proceso con ctrl+z en vez de ctrl+c ejecutar los siguientes comandos en cualquier terminal para matar los procesos:
    - chmod +x kill_all.sh
    - ./kill_all.sh
