import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


import main  


class CredencialesDialog(simpledialog.Dialog):
    def body(self, master):
        # Configura el título de la ventana
        self.title("Guardar Credenciales")
        # Crea etiquetas para los campos
        tk.Label(master, text="Usuario:").grid(row=0, sticky=tk.W)
        tk.Label(master, text="Contraseña:").grid(row=1, sticky=tk.W)
        # Crea campos de entrada
        self.usuario = tk.Entry(master)
        self.contrasena = tk.Entry(master, show="*")
        # Posiciona los campos de entrada en la grilla
        self.usuario.grid(row=0, column=1)
        self.contrasena.grid(row=1, column=1)

        return self.usuario  # Foco inicial

    def apply(self):
        self.result = {
            "USER": self.usuario.get().strip(),
            "PASS": self.contrasena.get().strip()
        }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # Configuración de la ventana principal
        self.title("CE1121") # Título de la aplicación
        self.geometry("400x350")  # Tamaño de ventana (ancho x alto)
        self.resizable(False, False) # Impide redimensionar la ventana
        # Variables de estado
        self.worker_thread = None # Hilo para ejecutar procesos en segundo plano
        self.estado_var = tk.StringVar(value="Estado: Esperando acción") # Variable para mostrar estado
        # Crea todos los elementos de la interfaz
        self.crear_widgets()

    def crear_widgets(self):
        # Frame principal con padding para mejor apariencia
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        # Etiqueta que muestra el estado actual del proceso
        self.estado_label = ttk.Label(frame, textvariable=self.estado_var, anchor="center")
        self.estado_label.pack(pady=5, fill=tk.X)
        # Barra de progreso (inicialmente oculta)
        self.progress = ttk.Progressbar(frame, mode="indeterminate") # Modo indeterminado (animación continua)
        self.progress.pack(pady=5, fill=tk.X)
        self.progress.stop() # Detiene la animación
        self.progress.pack_forget() # Oculta la barra inicialmente
        # Botón para guardar credenciales
        ttk.Button(frame, text="Guardar Credenciales", command=self.guardar_credenciales).pack(pady=2, fill=tk.X)
        # Botón principal para ejecutar el proceso
        self.boton_ejecutar = ttk.Button(frame, text="Ejecutar Proceso Principal", command=self.iniciar_proceso)
        self.boton_ejecutar.pack(pady=2, fill=tk.X)
        # Botón para cancelar proceso en ejecución (inicialmente deshabilitado)
        self.boton_cancelar = ttk.Button(frame, text="Cancelar Proceso", command=self.cancelar_proceso, state=tk.DISABLED)
        self.boton_cancelar.pack(pady=2, fill=tk.X)
        # Botón para reiniciar completamente el proceso
        ttk.Button(frame, text="Reiniciar Proceso", command=self.reiniciar_proceso).pack(pady=2, fill=tk.X)
        # Nuevo botón para reiniciar manteniendo referencia
        ttk.Button(frame, text="Reiniciar Manteniendo Referencia", command=self.reiniciar_con_referencia).pack(pady=2, fill=tk.X)
        # Botón para cerrar la aplicación completamente
        ttk.Button(frame, text="Cerrar Consola", command=self.cerrar_consola).pack(pady=2, fill=tk.X)

    
    def guardar_credenciales(self):
        dialog = CredencialesDialog(self)

        if dialog.result:
           user = dialog.result["USER"]
           password = dialog.result["PASS"]

           if not user or not password:
              messagebox.showwarning(
                  "Validación",
                  "Usuario y contraseña son obligatorios."
              )
              return

           try:
              from encriptador import guardar_credenciales
              import os
              import sys
              ruta = guardar_credenciales(user, password)

              self.estado_var.set("Credenciales guardadas correctamente.")
              messagebox.showinfo(
                  "Éxito",
                  f" Credenciales guardadas correctamente\n\nRuta:\n{ruta}"
              )
              
              os.execl(sys.executable, sys.executable, *sys.argv)
           except Exception as e:
               messagebox.showerror(
                   "Error",
                   f"No se pudieron guardar las credenciales:\n{e}"
                )
               
    def credenciales_existentes(self):
        """
        Verifica si existen credenciales guardadas en App/config/.env
        """
        import os
        base_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(base_dir, "config", ".env")
        return os.path.exists(env_path)

    def iniciar_proceso(self):
              
        if not self.credenciales_existentes():
            messagebox.showwarning(
                "Credenciales requeridas",
                "No hay credenciales guardadas.\n\n"
                "Por favor use el botón 'Guardar Credenciales' primero."
           )
            return

        # Actualiza el estado visual
        self.estado_var.set("Ejecutando proceso principal...")
        self.boton_ejecutar.config(state=tk.DISABLED) # Deshabilita el botón de ejecutar
        self.boton_cancelar.config(state=tk.NORMAL) # Habilita el botón de cancelar
        self.progress.pack() # Muestra la barra de progreso
        self.progress.start(10) # Inicia la animación de la barra
        # Flag para controlar la cancelación del proceso
        self._cancelar = False

        def tarea():
            try:
                self.actualizar_estado("Proceso iniciado...")
                # Llama al proceso principal del módulo main
                main.ejecutar_proceso()
                # Si no se canceló, muestra mensaje de éxito
                if not self._cancelar:
                    self.actualizar_estado("Proceso finalizado exitosamente.")
            except Exception as e:
                # Maneja cualquier error durante la ejecución
                self.actualizar_error(str(e))
            finally:
                # Siempre restaura el estado de la interfaz
                self.finalizar_proceso()
        # Crea y inicia el hilo separado (daemon=True para que termine con la app)
        self.worker_thread = threading.Thread(target=tarea, daemon=True)
        self.worker_thread.start()

    def cancelar_proceso(self):
        self._cancelar = True # Marca el flag de cancelación
        self.estado_var.set("Cancelando proceso...")
        self.boton_cancelar.config(state=tk.DISABLED) # Deshabilita el botón de cancelar

    def reiniciar_proceso(self):
        try:
            # Llama a la función de reinicio completo
            main.reiniciar_ejecucion()
            self.estado_var.set("Proceso reiniciado con éxito.")
            messagebox.showinfo("Reinicio Exitoso", "El proceso se ha reiniciado correctamente.")
            # Restaura el estado de los controles
            self.boton_ejecutar.config(state=tk.NORMAL)
            self.boton_cancelar.config(state=tk.DISABLED)
            self.progress.stop()
            self.progress.pack_forget()
        except Exception as e:
            # Maneja errores durante el reinicio
            self.estado_var.set(f"Error al reiniciar el proceso: {e}")
            messagebox.showerror("Error", f"Error al reiniciar el proceso: {e}")

    def reiniciar_con_referencia(self):
        try:
            # Llama a la función de reinicio manteniendo referencia
            main.reiniciar_ejecucion_con_referencia()
            self.estado_var.set("Proceso reiniciado manteniendo referencia.")
            messagebox.showinfo("Reinicio con Referencia", "El proceso se ha reiniciado manteniendo el excel de referencia.")
            # Restaura el estado de los controles
            self.boton_ejecutar.config(state=tk.NORMAL)
            self.boton_cancelar.config(state=tk.DISABLED)
            self.progress.stop()
            self.progress.pack_forget()
        except Exception as e:
            # Maneja errores durante el reinicio con referencia
            self.estado_var.set(f"Error al reiniciar con referencia: {e}")
            messagebox.showerror("Error", f"Error al reiniciar con referencia: {e}")

    def actualizar_estado(self, mensaje):
        self.estado_var.set(f"Estado: {mensaje}")

    def actualizar_error(self, mensaje):
        self.estado_var.set(f"Error: {mensaje}")
        messagebox.showerror("Error", mensaje)

    def finalizar_proceso(self):
        self.progress.stop() # Detiene la animación de la barra de progreso
        self.progress.pack_forget() # Oculta la barra de progreso
        self.boton_ejecutar.config(state=tk.NORMAL) # Habilita el botón de ejecutar
        self.boton_cancelar.config(state=tk.DISABLED) # Deshabilita el botón de cancelar

    def cerrar_consola(self):
        print("Cerrando la consola y la aplicación.")
        self.destroy() # Destruye la ventana
        sys.exit() # Termina el programa

# Punto de entrada del programa
if __name__ == "__main__":
    # Crea la instancia de la aplicación
    app = App()
    # Inicia el bucle principal de eventos de la interfaz gráfica
    app.mainloop()