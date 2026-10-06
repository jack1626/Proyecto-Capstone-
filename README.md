#  Capstone Web - Plataforma de Contratación de Servicios

> **Curso:** Capstone
> **Institución:** Duoc Uc (San Bernardo) 
> **Semestre / Año:** Segundo Semestre 2026

---

##  Descripción del Proyecto

Easy Office es una empresa que busca una aplicación web dinámica, escalable y segura. Por lo que de momento vamos a desarrollar un proyecto que automatiza el proceso de contratación y gestión de oficinas virtuales para emprendedores y empresas. En donde la plataforma permite a los usuarios explorar planes de servicios digitales (dirección tributaria, atención telefónica, uso de salas de reunión, entre otros), registrar sus empresas, realizar contrataciones en tiempo real y gestionar sus servicios activos desde un panel personalizado.

El sistema cuenta con una arquitectura basada en el patrón MVT (Modelo-Vista-Template) y un esquema de control de acceso por roles diferenciados, brindando una experiencia adaptada tanto para los clientes finales como para el personal ejecutivo/administrativo.

---

##  Integrantes del Equipo

* **[Angelo Sepulveda Diaz]** -- [@jack1626](https://github.com/jack1626)
* **[Ignacio Bizama Iturra]** -- [@NatsuEz](https://github.com/NatsuEz))

---

##  Tecnologías Utilizadas

* **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5, Django Templates
* **Backend:** Python (Django Web Framework)
* **Base de Datos:** SQLite / PostgreSQL (Django ORM)
* **Control de Versiones:** Git & GitHub

---

---

##  Requisitos e Instalación Local

### Prerrequisitos
Antes de comenzar, asegúrate de tener instalados los siguientes programas en tu equipo:

* **[Git](https://git-scm.com/downloads)**: Para la gestión de versiones y clonación del repositorio.
* **[Python 3.x](https://www.python.org/downloads/)**: Intérprete del lenguaje (marcar la opción *"Add Python to PATH"* durante la instalación).
* **[VS Code](https://code.visualstudio.com/)**: Editor de código recomendado.


---

### Ejecución Local (CMD / Windows)

Sigue esto en la consola de comandos de Windows (`cmd`) para desplegar y probar el proyecto en tu computadora (mac o linux tiene otra forma y ahora mismo no la se):

1. **Clonar el repositorio:**

   git clone [https://github.com/jack1626/Proyecto-Capstone-.git](https://github.com/jack1626/Proyecto-Capstone-.git)

   cd Proyecto-Capstone-

---

2. **Crear y activar el entorno virtual:**

   python -m venv venv
   
   venv\Scripts\activate

---

3. **Instalar dependencias:**

   pip install django

---

4. **Instalar dependencias:**

   cd src

   python manage.py migrate

   python manage.py runserver


---
##  Estructura del Repositorio

```text
Proyecto-Capstone/
├── docs/                        # Documentación académica por fases
│   ├── Fase 1/
│   │   ├── Documentación Proyecto/
│   │   └── Evidencias Angelo Sepulveda/
│   ├── Fase 2/
│   └── Fase 3/
├── src/                         # CÓDIGO FUENTE DE LA APLICACIÓN WEB
│   ├── capstone_web/            # Configuración principal (Django)
│   ├── servicios/               # Aplicación / módulos principales
│   └── manage.py                # Ejecutable principal
├── .gitignore                   # Archivos que Git debe ignorar (archivos temporales, virtualenv, etc.)
├── Intrucciones                 # Instrucciones para ejecutar la apliacion
└── README.md                    # Presentación principal del repositorio
