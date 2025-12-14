import pytest
from app.core.batch_processor import BatchProcessor


@pytest.mark.asyncio
class TestBatchProcessor:
    
    async def test_process_csv_file(self, db_session, sample_contract, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("user_id,email\nusr_123,test@example.com\nusr_456,test2@example.com")
        
        processor = BatchProcessor(db_session)
        result = await processor.process_file(
            contract_id=sample_contract.id,
            file_path=str(csv_file),
            file_type='csv'
        )
        
        assert result.total_records == 2
        assert result.batch_id is not None
    
    async def test_invalid_file_format(self, db_session, sample_contract, tmp_path):
        bad_file = tmp_path / "test.csv"
        bad_file.write_text("not csv format")
        
        processor = BatchProcessor(db_session)
        
        with pytest.raises(Exception):
            await processor.process_file(
                contract_id=sample_contract.id,
                file_path=str(bad_file),
                file_type='csv'
            )