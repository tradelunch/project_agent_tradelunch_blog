import { type TPostFileMeta } from '@repo/markdown-parsing/src/types';
import { Sequelize, Transaction } from "sequelize";

export const insertImage = async (
	db: Sequelize,
	meta: TPostFileMeta,
	tx: Transaction
) => {
	await db.query(
		`
        INSERT INTO 
            files (id, user_id, post_id, content_type, ext, original_filename, stored_name, stored_uri, file_size, is_thumbnail, created_at, updated_at, deleted_at)
            VALUES (:id, :user_id, :post_id, :content_type, :ext, :original_filename, :stored_name, :stored_uri, :file_size, :is_thumbnail, NOW(), NOW(), NULL)
        `,
		{
			replacements: {
				id: meta.id!,
				post_id: meta.postId!,
				user_id: meta.userId!,
				content_type: meta.contentType,
				ext: meta.ext,
				original_filename: meta.filename,
				stored_name: meta.storedName,
				stored_uri: meta.storedUri,
				file_size: meta.fileSize,
				is_thumbnail: true,
			},
			transaction: tx,
		}
	);
	console.log(`Inserted image meta for post_id=${meta.postId}`);
};
