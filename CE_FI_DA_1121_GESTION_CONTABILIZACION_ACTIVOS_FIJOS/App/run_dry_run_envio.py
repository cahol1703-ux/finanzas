from pathlib import Path
import sys
import pandas as pd

# Asegurar que App está en sys.path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from Functions import envio_correos


def main():
    data_dir = HERE / "Data" / "temp_dry"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Archivo de datos con columna 'Responsable'
    df = pd.DataFrame({
        'Responsable': ['Alice', 'Bob', 'Charlie'],
        'Cuenta': [100, 200, 300],
    })
    data_file = data_dir / 'data.xlsx'
    df.to_excel(data_file, index=False)

    # Archivo de reglas: primera columna responsable, segunda columna correo
    reglas_df = pd.DataFrame([
        ['Alice', 'alice@example.com'],
        ['Bob', 'bob@example.com'],
        # Charlie intentionally left out to test warning
    ])
    reglas_file = data_dir / 'reglas.xlsx'
    reglas_df.to_excel(reglas_file, index=False, header=False)

    print('Archivos creados:')
    print(data_file)
    print(reglas_file)

    envio_correos.procesar_envio(str(data_file), str(reglas_file), 0, str(data_dir), dry_run=True, use_outlook=False)


if __name__ == '__main__':
    main()
